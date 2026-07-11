import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request, UploadFile, File
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.templates_setup import templates
from app.models.models import User, Essay, CorrectionTemplate
from app.services.ocr_service import extract_text_from_file

router = APIRouter()

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def _require_user(request: Request, db: Session = Depends(get_db)):
    """Redirect to login if not authenticated."""
    user = get_current_user(request, db)
    if user is None:
        return None  # caller handles redirect
    return user


# ── Upload page ──────────────────────────────────────────────────────────────

@router.get("/upload")
def upload_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=302)

    correction_templates = (
        db.query(CorrectionTemplate)
        .filter(
            (CorrectionTemplate.is_default == True)
            | (CorrectionTemplate.created_by == user.id)
        )
        .order_by(CorrectionTemplate.is_default.desc(), CorrectionTemplate.name)
        .all()
    )

    return templates.TemplateResponse(
        "upload.html",
        {"request": request, "correction_templates": correction_templates, "user": user},
    )


# ── Paste text ───────────────────────────────────────────────────────────────

@router.post("/upload/text")
def upload_text(
    request: Request,
    raw_text: str = Form(...),
    template_id: int = Form(...),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=302)

    essay = Essay(
        user_id=user.id,
        source_type="pasted",
        raw_text=raw_text.strip(),
        status="pending_correction",
        template_id=template_id,
    )
    db.add(essay)
    db.commit()
    db.refresh(essay)

    return RedirectResponse(url=f"/correction/start/{essay.id}", status_code=302)


# ── Upload file ──────────────────────────────────────────────────────────────

@router.post("/upload/file")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    template_id: int = Form(...),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=302)

    # Validate extension
    original_name = file.filename or "file"
    ext = Path(original_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return templates.TemplateResponse(
            "upload.html",
            {
                "request": request,
                "error": f"Formato não suportado: {ext}. Use PDF, JPG ou PNG.",
            },
        )

    # Read content and validate size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        return templates.TemplateResponse(
            "upload.html",
            {
                "request": request,
                "error": "Arquivo muito grande. O limite é 10 MB.",
            },
        )

    # Save file with unique name
    unique_name = f"{uuid.uuid4().hex}_{original_name}"
    file_path = str(UPLOAD_DIR / unique_name)
    with open(file_path, "wb") as f:
        f.write(content)

    # Create Essay with pending_review
    essay = Essay(
        user_id=user.id,
        filename=original_name,
        source_type="scanned",
        status="pending_review",
        template_id=template_id,
    )
    db.add(essay)
    db.commit()
    db.refresh(essay)

    # Extract text via OCR
    try:
        extracted = await extract_text_from_file(file_path, ext)
    except Exception as exc:
        extracted = f"[Erro ao processar arquivo: {exc}]"

    # Update essay with extracted text
    essay.raw_text = extracted
    db.commit()

    return RedirectResponse(url=f"/review/{essay.id}", status_code=302)


# ── Review ───────────────────────────────────────────────────────────────────

@router.get("/review/{essay_id}")
def review_page(
    request: Request,
    essay_id: int,
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=302)

    essay = db.query(Essay).filter(Essay.id == essay_id, Essay.user_id == user.id).first()
    if essay is None:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "message": "Redação não encontrada."},
            status_code=404,
        )

    return templates.TemplateResponse(
        "review.html",
        {"request": request, "essay": essay},
    )


@router.post("/review/{essay_id}")
def review_submit(
    request: Request,
    essay_id: int,
    raw_text: str = Form(...),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=302)

    essay = db.query(Essay).filter(Essay.id == essay_id, Essay.user_id == user.id).first()
    if essay is None:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "message": "Redação não encontrada."},
            status_code=404,
        )

    essay.raw_text = raw_text.strip()
    essay.status = "pending_correction"
    db.commit()

    return RedirectResponse(url=f"/correction/start/{essay.id}", status_code=302)
