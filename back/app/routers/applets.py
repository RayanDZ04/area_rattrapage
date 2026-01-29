from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import SessionLocal
from .. import models, schemas
from .auth import get_current_user

router = APIRouter(prefix="/applets", tags=["applets"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("", response_model=schemas.AppletOut, status_code=status.HTTP_201_CREATED)
def create_applet(
    payload: schemas.AppletCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    applet = models.Applet(
        user_id=current_user.id,
        name=payload.name,
        action_service=payload.action_service,
        action_choice=payload.action_choice,
        reaction_service=payload.reaction_service,
        reaction_choice=payload.reaction_choice,
    )
    db.add(applet)
    db.commit()
    db.refresh(applet)
    return applet


@router.get("", response_model=list[schemas.AppletOut])
def list_applets(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return (
        db.query(models.Applet)
        .filter(models.Applet.user_id == current_user.id)
        .order_by(models.Applet.created_at.desc())
        .all()
    )


@router.delete("/{applet_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_applet(
    applet_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    applet = (
        db.query(models.Applet)
        .filter(models.Applet.id == applet_id, models.Applet.user_id == current_user.id)
        .first()
    )
    if not applet:
        raise HTTPException(status_code=404, detail="Applet not found")
    db.delete(applet)
    db.commit()
    return None
