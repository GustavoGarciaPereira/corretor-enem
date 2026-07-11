from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.templates_setup import templates
from app.models.models import Essay
from app.services.correction_service import perform_double_correction

router = APIRouter()


@router.get("/correction/start/{essay_id}")
async def correction_start(
    request: Request,
    essay_id: int,
    db: Session = Depends(get_db),
):
    """Trigger the dual-correction pipeline for an essay."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=302)

    essay = (
        db.query(Essay)
        .filter(Essay.id == essay_id, Essay.user_id == user.id)
        .first()
    )
    if essay is None:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "message": "Redação não encontrada."},
            status_code=404,
        )

    if essay.status != "pending_correction":
        return RedirectResponse(url=f"/result/{essay_id}", status_code=302)

    await perform_double_correction(essay.id, essay.raw_text or "")

    return RedirectResponse(url=f"/result/{essay_id}", status_code=302)
