from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import User


def get_current_user(request: Request, db: Session = Depends(get_db)):
    """Dependency: return the logged-in User or None."""
    user_id = request.session.get("user_id")
    if user_id is None:
        return None
    return db.query(User).filter(User.id == user_id).first()


def require_user(user: User = Depends(get_current_user)):
    """Dependency: require an authenticated user or raise 403."""
    if user is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Not authenticated")
    return user
