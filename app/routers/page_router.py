from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.templates_setup import templates
from app.models.models import User, Essay, Correction

router = APIRouter()


# ─── Dashboard ───────────────────────────────────────────────────────────────

@router.get("/dashboard")
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=302)

    essays = (
        db.query(Essay)
        .filter(Essay.user_id == user.id)
        .order_by(Essay.created_at.desc())
        .all()
    )

    # Fetch correction scores per essay for the table
    essay_scores = {}  # essay_id -> {"a": int|None, "b": int|None}
    if essays:
        essay_ids = [e.id for e in essays]
        corrections = (
            db.query(Correction)
            .filter(
                Correction.essay_id.in_(essay_ids),
                Correction.corrector_type.in_(["A", "B"]),
            )
            .all()
        )
        for cor in corrections:
            if cor.essay_id not in essay_scores:
                essay_scores[cor.essay_id] = {"a": None, "b": None}
            key = "a" if cor.corrector_type == "A" else "b"
            essay_scores[cor.essay_id][key] = cor.total_score

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "essays": essays,
            "essay_scores": essay_scores,
            "user": user,
        },
    )


# ─── Result ──────────────────────────────────────────────────────────────────

@router.get("/result/{essay_id}")
def result_page(
    request: Request,
    essay_id: int,
    db: Session = Depends(get_db),
):
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

    corrections = (
        db.query(Correction)
        .filter(Correction.essay_id == essay_id)
        .order_by(Correction.corrector_type)
        .all()
    )

    has_c = any(c.corrector_type == "C" for c in corrections)

    return templates.TemplateResponse(
        "result.html",
        {
            "request": request,
            "essay": essay,
            "corrections": corrections,
            "has_c": has_c,
        },
    )


# ─── Stats ───────────────────────────────────────────────────────────────────

@router.get("/stats")
def stats(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=302)

    # Aggregate average score per competency across all completed essays
    rows = (
        db.query(
            Essay.created_at,
            func.avg(Correction.c1).label("c1"),
            func.avg(Correction.c2).label("c2"),
            func.avg(Correction.c3).label("c3"),
            func.avg(Correction.c4).label("c4"),
            func.avg(Correction.c5).label("c5"),
            func.avg(Correction.total_score).label("total"),
        )
        .join(Correction, Correction.essay_id == Essay.id)
        .filter(
            Essay.user_id == user.id,
            Essay.status == "completed",
        )
        .group_by(Essay.id)
        .order_by(Essay.created_at)
        .all()
    )

    # Serialize for Chart.js
    dates = [r.created_at.strftime("%d/%m") for r in rows]
    c1_data = [round(r.c1 or 0) for r in rows]
    c2_data = [round(r.c2 or 0) for r in rows]
    c3_data = [round(r.c3 or 0) for r in rows]
    c4_data = [round(r.c4 or 0) for r in rows]
    c5_data = [round(r.c5 or 0) for r in rows]
    total_data = [round(r.total or 0) for r in rows]

    # Also compute overall averages for summary cards
    total_essays = len(rows)
    if total_essays > 0:
        avg_c1 = sum(c1_data) // total_essays
        avg_c2 = sum(c2_data) // total_essays
        avg_c3 = sum(c3_data) // total_essays
        avg_c4 = sum(c4_data) // total_essays
        avg_c5 = sum(c5_data) // total_essays
        avg_total = sum(total_data) // total_essays
    else:
        avg_c1 = avg_c2 = avg_c3 = avg_c4 = avg_c5 = avg_total = 0

    return templates.TemplateResponse(
        "stats.html",
        {
            "request": request,
            "dates": dates,
            "c1_data": c1_data,
            "c2_data": c2_data,
            "c3_data": c3_data,
            "c4_data": c4_data,
            "c5_data": c5_data,
            "total_data": total_data,
            "avg_c1": avg_c1,
            "avg_c2": avg_c2,
            "avg_c3": avg_c3,
            "avg_c4": avg_c4,
            "avg_c5": avg_c5,
            "avg_total": avg_total,
            "total_essays": total_essays,
            "user": user,
        },
    )
