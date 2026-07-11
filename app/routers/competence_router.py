from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.templates_setup import templates
from app.models.models import User, Competence, Level, TemplateCompetence

router = APIRouter()


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


# ─── Levels JSON ─────────────────────────────────────────────────────────────

@router.get("/competences/{comp_id}/levels")
def get_competence_levels(comp_id: int, db: Session = Depends(get_db)):
    comp = db.query(Competence).filter(Competence.id == comp_id).first()
    if not comp:
        return JSONResponse({"error": "Not found"}, status_code=404)
    levels = [
        {"level_index": l.level_index, "score": l.score, "description": l.description}
        for l in sorted(comp.levels, key=lambda x: x.level_index)
    ]
    return JSONResponse({"name": comp.name, "levels": levels})


# ─── New form ────────────────────────────────────────────────────────────────

@router.get("/competences/new")
def new_competence_form(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=302)

    default_levels = [
        {"level_index": i, "score": i * 40, "description": ""} for i in range(6)
    ]

    return templates.TemplateResponse(
        "competence_form.html",
        {"request": request, "comp": None, "levels": default_levels, "user": user},
    )


# ─── Create ──────────────────────────────────────────────────────────────────

@router.post("/competences")
async def create_competence(
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
    db.flush()

    form_data = await request.form()
    for i in range(6):
        score_val = form_data.get(f"level_{i}_score")
        desc_val = form_data.get(f"level_{i}_desc")
        if score_val and desc_val:
            level = Level(
                competence_id=comp.id,
                level_index=i,
                score=int(str(score_val)),
                description=str(desc_val).strip(),
            )
            db.add(level)

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

    levels_by_index = {l.level_index: l for l in (comp.levels or [])}
    levels_list = [levels_by_index.get(i) for i in range(6)]

    return templates.TemplateResponse(
        "competence_form.html",
        {"request": request, "comp": comp, "levels": levels_list, "user": user},
    )


# ─── Update ──────────────────────────────────────────────────────────────────

@router.post("/competences/{comp_id}/edit")
async def update_competence(
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

    # Replace levels
    db.query(Level).filter(Level.competence_id == comp_id).delete()
    form_data = await request.form()
    for i in range(6):
        score_val = form_data.get(f"level_{i}_score")
        desc_val = form_data.get(f"level_{i}_desc")
        if score_val and desc_val:
            level = Level(
                competence_id=comp_id,
                level_index=i,
                score=int(str(score_val)),
                description=str(desc_val).strip(),
            )
            db.add(level)

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

    in_use = (
        db.query(TemplateCompetence)
        .filter(TemplateCompetence.competence_id == comp_id)
        .first()
    )
    if in_use:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "message": "Competência está vinculada a um template."},
            status_code=400,
        )

    db.delete(comp)
    db.commit()
    return RedirectResponse(url="/competences", status_code=302)
