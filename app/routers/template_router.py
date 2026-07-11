from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.templates_setup import templates
from app.models.models import (
    User,
    Competence,
    CorrectionTemplate,
    TemplateCompetence,
    Essay,
)

router = APIRouter()


# ─── List ────────────────────────────────────────────────────────────────────

@router.get("/templates")
def list_templates(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=302)

    templates_list = (
        db.query(CorrectionTemplate)
        .filter(
            (CorrectionTemplate.is_default == True)
            | (CorrectionTemplate.created_by == user.id)
        )
        .order_by(CorrectionTemplate.is_default.desc(), CorrectionTemplate.name)
        .all()
    )

    essay_counts = {}
    for t in templates_list:
        essay_counts[t.id] = (
            db.query(Essay).filter(Essay.template_id == t.id).count()
        )

    return templates.TemplateResponse(
        "templates.html",
        {
            "request": request,
            "templates": templates_list,
            "essay_counts": essay_counts,
            "user": user,
        },
    )


# ─── Create form ─────────────────────────────────────────────────────────────

@router.get("/templates/new")
def new_template_form(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=302)

    competences = (
        db.query(Competence)
        .filter(
            (Competence.is_default == True) | (Competence.created_by == user.id)
        )
        .order_by(Competence.name)
        .all()
    )

    return templates.TemplateResponse(
        "template_form.html",
        {"request": request, "template": None, "competences": competences, "user": user},
    )


# ─── Create ──────────────────────────────────────────────────────────────────

@router.post("/templates")
def create_template(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    competence_ids: list[int] = Form([]),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=302)

    template = CorrectionTemplate(
        name=name,
        description=description,
        created_by=user.id,
    )
    db.add(template)
    db.flush()

    for cid in competence_ids:
        db.add(TemplateCompetence(template_id=template.id, competence_id=cid))

    db.commit()

    return RedirectResponse(url="/templates", status_code=302)


# ─── Edit form ───────────────────────────────────────────────────────────────

@router.get("/templates/{tid}/edit")
def edit_template_form(
    request: Request,
    tid: int,
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=302)

    template = db.query(CorrectionTemplate).filter(CorrectionTemplate.id == tid).first()
    if template is None:
        return templates.TemplateResponse(
            "error.html", {"request": request, "message": "Template não encontrado."},
            status_code=404,
        )

    all_competences = (
        db.query(Competence)
        .filter(
            (Competence.is_default == True) | (Competence.created_by == user.id)
        )
        .order_by(Competence.name)
        .all()
    )

    selected_ids = {tc.id for tc in template.competences}

    return templates.TemplateResponse(
        "template_form.html",
        {
            "request": request,
            "template": template,
            "competences": all_competences,
            "selected_ids": selected_ids,
            "user": user,
        },
    )


# ─── Update ──────────────────────────────────────────────────────────────────

@router.post("/templates/{tid}/edit")
def update_template(
    request: Request,
    tid: int,
    name: str = Form(...),
    description: str = Form(""),
    competence_ids: list[int] = Form([]),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=302)

    template = db.query(CorrectionTemplate).filter(CorrectionTemplate.id == tid).first()
    if template is None:
        return templates.TemplateResponse(
            "error.html", {"request": request, "message": "Template não encontrado."},
            status_code=404,
        )
    if template.is_default:
        return templates.TemplateResponse(
            "error.html", {"request": request, "message": "Template padrão não pode ser editado."},
            status_code=403,
        )
    if template.created_by != user.id:
        return templates.TemplateResponse(
            "error.html", {"request": request, "message": "Permissão negada."},
            status_code=403,
        )

    template.name = name
    template.description = description

    # Re-associate competences: clear and re-add
    db.query(TemplateCompetence).filter(
        TemplateCompetence.template_id == tid
    ).delete()
    for cid in competence_ids:
        db.add(TemplateCompetence(template_id=tid, competence_id=cid))

    db.commit()

    return RedirectResponse(url="/templates", status_code=302)


# ─── Delete ──────────────────────────────────────────────────────────────────

@router.post("/templates/{tid}/delete")
def delete_template(
    request: Request,
    tid: int,
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=302)

    template = db.query(CorrectionTemplate).filter(CorrectionTemplate.id == tid).first()
    if template is None:
        return templates.TemplateResponse(
            "error.html", {"request": request, "message": "Template não encontrado."},
            status_code=404,
        )
    if template.is_default:
        return templates.TemplateResponse(
            "error.html", {"request": request, "message": "Template padrão não pode ser excluído."},
            status_code=403,
        )

    in_use = db.query(Essay).filter(Essay.template_id == tid).first()
    if in_use:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "message": "Template está em uso por uma redação. Não pode ser excluído."},
            status_code=400,
        )

    # Cascade deletes TemplateCompetence rows automatically
    db.delete(template)
    db.commit()

    return RedirectResponse(url="/templates", status_code=302)
