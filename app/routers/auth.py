from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import bcrypt as _bcrypt

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.templates_setup import templates
from app.models.models import User, Essay

router = APIRouter()


# ── Pages ────────────────────────────────────────────────────────────────────

@router.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/register")
def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


# ── Actions ──────────────────────────────────────────────────────────────────

@router.post("/register")
def register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    # Check if user already exists
    existing = db.query(User).filter(
        (User.username == username) | (User.email == email)
    ).first()
    if existing:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Usuário ou email já cadastrado."},
        )

    hashed = _bcrypt.hashpw(password.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")
    user = User(
        username=username,
        email=email,
        password_hash=hashed,
    )
    db.add(user)
    db.commit()
    return RedirectResponse(url="/login", status_code=302)


@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == username).first()
    if not user or not _bcrypt.checkpw(
        password.encode("utf-8"), user.password_hash.encode("utf-8")
    ):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Usuário ou senha inválidos."},
        )

    request.session["user_id"] = user.id
    return RedirectResponse(url="/dashboard", status_code=302)


@router.get("/dashboard")
def dashboard(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if user_id is None:
        return RedirectResponse(url="/login", status_code=302)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        request.session.clear()
        return RedirectResponse(url="/login", status_code=302)

    essays = (
        db.query(Essay)
        .filter(Essay.user_id == user_id)
        .order_by(Essay.created_at.desc())
        .all()
    )

    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "essays": essays, "user": user},
    )


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)
