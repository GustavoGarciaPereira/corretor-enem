from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.templates_setup import templates
from app.models.models import User, Competence, TemplateCompetence

router = APIRouter()


def _require(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user is None:
        return None
    return user


# ─── List ────────────────────────────────────────────────────────────────────

@router.get("/competences")
def list_competences(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=302)

    competences = (
        db.query(Competence)
        .filter(
            (Competence.is_default == True) | (Competence.created_by == user.id)
        )
        .order_by(Competence.is_default.desc(), Competence.name)
        .all()
    )

    return templates.TemplateResponse(
        "competences.html",
        {"request": request, "competences": competences, "user": user},
    )


# ─── Create ──────────────────────────────────────────────────────────────────

@router.post("/competences")
def create_competence(
    request: Request,
    name: str = Form(...),
    description: str = Form(...),
    max_score: int = Form(200),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=302)

    comp = Competence(
        name=name,
        description=description,
        max_score=max_score,
        created_by=user.id,
    )
    db.add(comp)
    db.commit()

    return RedirectResponse(url="/competences", status_code=302)


# ─── Edit form ───────────────────────────────────────────────────────────────

@router.get("/competences/{comp_id}/edit")
def edit_competence_form(
    request: Request,
    comp_id: int,
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=302)

    comp = db.query(Competence).filter(Competence.id == comp_id).first()
    if comp is None or (comp.is_default and comp.created_by is not None):
        return templates.TemplateResponse(
            "error.html", {"request": request, "message": "Competência não encontrada."},
            status_code=404,
        )

    return templates.TemplateResponse(
        "competence_form.html",
        {"request": request, "comp": comp, "user": user},
    )


# ─── Update ──────────────────────────────────────────────────────────────────

@router.post("/competences/{comp_id}/edit")
def update_competence(
    request: Request,
    comp_id: int,
    name: str = Form(...),
    description: str = Form(...),
    max_score: int = Form(200),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=302)

    comp = db.query(Competence).filter(Competence.id == comp_id).first()
    if comp is None:
        return templates.TemplateResponse(
            "error.html", {"request": request, "message": "Competência não encontrada."},
            status_code=404,
        )
    if comp.is_default:
        return templates.TemplateResponse(
            "error.html", {"request": request, "message": "Competências padrão não podem ser editadas."},
            status_code=403,
        )
    if comp.created_by != user.id:
        return templates.TemplateResponse(
            "error.html", {"request": request, "message": "Permissão negada."},
            status_code=403,
        )

    comp.name = name
    comp.description = description
    comp.max_score = max_score
    db.commit()

    return RedirectResponse(url="/competences", status_code=302)


# ─── Delete ──────────────────────────────────────────────────────────────────

@router.post("/competences/{comp_id}/delete")
def delete_competence(
    request: Request,
    comp_id: int,
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=302)

    comp = db.query(Competence).filter(Competence.id == comp_id).first()
    if comp is None:
        return templates.TemplateResponse(
            "error.html", {"request": request, "message": "Competência não encontrada."},
            status_code=404,
        )
    if comp.is_default:
        return templates.TemplateResponse(
            "error.html", {"request": request, "message": "Competências padrão não podem ser excluídas."},
            status_code=403,
        )
    if comp.created_by != user.id:
        return templates.TemplateResponse(
            "error.html", {"request": request, "message": "Permissão negada."},
            status_code=403,
        )

    # Check if in use by any template
    in_use = (
        db.query(TemplateCompetence)
        .filter(TemplateCompetence.competence_id == comp_id)
        .first()
    )
    if in_use:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "message": "Competência está vinculada a um template. Remova-a do template primeiro."},
            status_code=400,
        )

    db.delete(comp)
    db.commit()

    return RedirectResponse(url="/competences", status_code=302)
