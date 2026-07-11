import base64
import io
from pathlib import Path

import httpx
from PIL import Image

from app.core.config import settings


def _image_to_base64(image_path: str) -> str:
    """Open an image with Pillow and return its base64-encoded PNG string."""
    with Image.open(image_path) as img:
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")


def _extract_pdf_text_direct(pdf_path: str) -> str:
    """Try to extract text from a PDF using PyPDF2."""
    from PyPDF2 import PdfReader

    reader = PdfReader(pdf_path)
    text_parts = []
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            text_parts.append(extracted)
    return "\n".join(text_parts).strip()


def _convert_pdf_to_images(pdf_path: str) -> list[str]:
    """Convert each page of a PDF to a PNG and return the file paths."""
    from pdf2image import convert_from_path

    images = convert_from_path(pdf_path, dpi=200)
    output_paths = []
    base = Path(pdf_path).with_suffix("")
    for i, img in enumerate(images):
        page_path = f"{base}_page_{i}.png"
        img.save(page_path, "PNG")
        output_paths.append(page_path)
    return output_paths


async def _call_deepseek_vision(
    image_base64: str, system_prompt: str = None
) -> str:
    """Send an image to the DeepSeek vision model and return the transcribed text."""
    if not settings.DEEPSEEK_API_KEY or settings.DEEPSEEK_API_KEY.startswith("sk-placeholder"):
        return "[ERRO] Chave da API DeepSeek não configurada."

    USER_PROMPT = (
        "Transcreva exatamente a redação do ENEM. "
        "Mantenha parágrafos, acentos e pontuação. Retorne APENAS o texto."
    )

    headers = {
        "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": system_prompt or USER_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_base64}"
                        },
                    },
                ],
            }
        ],
        "max_tokens": 4096,
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            "https://api.deepseek.com/chat/completions",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        # Strip markdown code fences if present
        if content.startswith("```"):
            content = content.split("\n", 1)[-1]
            content = content.rsplit("```", 1)[0]
        return content.strip()


async def extract_text_from_file(file_path: str, file_ext: str) -> str:
    """Extract text from a PDF or image file using OCR or direct extraction.

    - PDF: try PyPDF2 first; if empty, convert to images and use DeepSeek vision.
    - Images (jpg/png): use DeepSeek vision directly.
    """
    ext = file_ext.lower()

    if ext == ".pdf":
        # Step 1: try direct text extraction
        text = _extract_pdf_text_direct(file_path)
        if text:
            return text

        # Step 2: convert PDF pages to images and OCR each
        page_images = _convert_pdf_to_images(file_path)
        texts = []
        for img_path in page_images:
            b64 = _image_to_base64(img_path)
            page_text = await _call_deepseek_vision(b64)
            texts.append(page_text)
            # Clean up temporary image
            Path(img_path).unlink(missing_ok=True)
        return "\n\n".join(texts).strip()

    elif ext in (".jpg", ".jpeg", ".png"):
        b64 = _image_to_base64(file_path)
        return await _call_deepseek_vision(b64)

    else:
        raise ValueError(f"Unsupported file extension: {ext}")
