import base64
import json
from datetime import datetime, timedelta
from email.utils import parseaddr
from email.message import EmailMessage

from fastapi import APIRouter, Depends, HTTPException, status
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from sqlalchemy.orm import Session

from ..database import SessionLocal
from .. import models, schemas
from .auth import get_current_user
from .auth import get_env

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
        action_config=json.dumps(payload.action_config),
        reaction_config=json.dumps(payload.reaction_config),
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
    applets = (
        db.query(models.Applet)
        .filter(models.Applet.user_id == current_user.id)
        .order_by(models.Applet.created_at.desc())
        .all()
    )
    for applet in applets:
        applet.action_config = json.loads(applet.action_config or "{}")
        applet.reaction_config = json.loads(applet.reaction_config or "{}")
    return applets


@router.patch("/{applet_id}/active", response_model=schemas.AppletOut)
def set_applet_active(
    applet_id: int,
    payload: schemas.AppletActiveUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    applet = (
        db.query(models.Applet)
        .filter(models.Applet.id == applet_id, models.Applet.user_id == current_user.id)
        .first()
    )
    if not applet:
        raise HTTPException(status_code=404, detail="Applet introuvable")
    applet.is_active = bool(payload.is_active)
    db.commit()
    db.refresh(applet)
    applet.action_config = json.loads(applet.action_config or "{}")
    applet.reaction_config = json.loads(applet.reaction_config or "{}")
    return applet


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
        raise HTTPException(status_code=404, detail="Applet introuvable")
    db.delete(applet)
    db.commit()
    return None


@router.get("/logs", response_model=list[schemas.AppletLogOut])
def list_logs(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return (
        db.query(models.AppletLog)
        .filter(models.AppletLog.user_id == current_user.id)
        .order_by(models.AppletLog.created_at.desc())
        .limit(100)
        .all()
    )


def get_google_credentials(db: Session, user_id: int) -> Credentials:
    token = (
        db.query(models.ServiceToken)
        .filter(models.ServiceToken.user_id == user_id, models.ServiceToken.provider == "google")
        .order_by(models.ServiceToken.created_at.desc())
        .first()
    )
    if not token:
        raise HTTPException(status_code=400, detail="Service Google non connecté")
    if not token.refresh_token:
        raise HTTPException(
            status_code=400,
            detail="Token Google incomplet. Reconnecte Google avec l'accès hors ligne.",
        )

    client_id = get_env("GOOGLE_CLIENT_ID")
    client_secret = get_env("GOOGLE_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise HTTPException(status_code=500, detail="Google OAuth non configuré sur le serveur")

    credentials = Credentials(
        token=token.access_token,
        refresh_token=token.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=[
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.modify",
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/calendar.readonly",
            "https://www.googleapis.com/auth/calendar.events",
        ],
    )

    should_refresh = token.created_at is None
    if token.created_at is not None:
        should_refresh = (datetime.utcnow() - token.created_at) > timedelta(minutes=50)

    if should_refresh:
        try:
            credentials.refresh(Request())
        except RefreshError as exc:
            raise HTTPException(status_code=400, detail="Token Google expiré. Reconnecte Google.") from exc
        token.access_token = credentials.token or token.access_token
        token.created_at = datetime.utcnow()
        db.commit()

    return credentials


def log_applet(db: Session, user_id: int, applet_id: int, status: str, message: str):
    db.add(
        models.AppletLog(
            user_id=user_id,
            applet_id=applet_id,
            status=status,
            message=message,
        )
    )
    db.commit()


def normalize_error_message(message: str) -> str:
    if not message:
        return "Erreur inconnue"
    lowered = message.lower()
    if "accessnotconfigured" in message or "has not been used in project" in lowered:
        if "gmail.googleapis.com" in lowered:
            return (
                "L'API Gmail est désactivée (ou jamais activée) sur ton projet Google Cloud. "
                "Active 'Gmail API' dans Google Cloud Console (APIs & Services → Library), "
                "attends 2-5 minutes, puis reconnecte Google."
            )
        if "calendar.googleapis.com" in lowered:
            return (
                "L'API Google Calendar est désactivée (ou jamais activée) sur ton projet Google Cloud. "
                "Active 'Google Calendar API' dans Google Cloud Console (APIs & Services → Library), "
                "attends 2-5 minutes, puis reconnecte Google."
            )
        return (
            "Une API Google est désactivée sur ton projet Google Cloud. "
            "Active les APIs nécessaires (Gmail/Calendar) puis réessaie."
        )
    if "The credentials do not contain the necessary fields need to refresh the access token" in message:
        return (
            "Identifiants Google incomplets pour rafraîchir le token. "
            "Reconnecte Google pour obtenir un refresh_token."
        )
    if "invalid_grant" in lowered:
        return "Autorisation Google expirée ou révoquée. Reconnecte Google."
    if "unauthorized" in lowered or "permission" in lowered or "insufficientpermissions" in lowered:
        return "Accès Google refusé. Vérifie les scopes / reconnecte Google."
    return message


def get_header_value(headers: list[dict], name: str) -> str:
    for header in headers:
        if header.get("name", "").lower() == name.lower():
            return header.get("value", "")
    return ""


def extract_email_address(value: str) -> str:
    if not value:
        return ""
    _, addr = parseaddr(value)
    return addr or value


def run_gmail_action(credentials: Credentials, applet: models.Applet, db: Session, config: dict) -> dict | None:
    gmail = build("gmail", "v1", credentials=credentials)
    query = "is:unread in:inbox"
    from_email = (config or {}).get("from_email") or ""
    if from_email:
        query = f"{query} from:{from_email}"
    result = gmail.users().messages().list(userId="me", maxResults=1, q=query).execute()
    messages = result.get("messages", [])
    if not messages:
        return None
    message_id = messages[0]["id"]
    if applet.last_action_marker == message_id:
        return None
    message = (
        gmail.users()
        .messages()
        .get(userId="me", id=message_id, format="metadata", metadataHeaders=["From", "Subject"])
        .execute()
    )
    headers = message.get("payload", {}).get("headers", [])
    return {
        "message_id": message_id,
        "from": get_header_value(headers, "From"),
        "subject": get_header_value(headers, "Subject"),
    }


def run_calendar_action(credentials: Credentials, applet: models.Applet, db: Session, config: dict) -> dict | None:
    calendar = build("calendar", "v3", credentials=credentials)
    calendar_id = (config or {}).get("calendar") or "primary"
    events = (
        calendar.events()
        .list(calendarId=calendar_id, maxResults=1, singleEvents=True, orderBy="updated")
        .execute()
        .get("items", [])
    )
    if not events:
        return None
    event_id = events[0]["id"]
    if applet.last_action_marker == event_id:
        return None
    return {"event_id": event_id, "calendar_id": calendar_id}


def mark_gmail_read(credentials: Credentials, message_id: str):
    gmail = build("gmail", "v1", credentials=credentials)
    gmail.users().messages().modify(
        userId="me", id=message_id, body={"removeLabelIds": ["UNREAD"]}
    ).execute()


def run_gmail_reaction(credentials: Credentials, config: dict):
    gmail = build("gmail", "v1", credentials=credentials)
    msg = EmailMessage()
    msg["To"] = config.get("to", "")
    msg["Subject"] = config.get("subject", "")
    msg.set_content(config.get("message", ""))
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    gmail.users().messages().send(userId="me", body={"raw": raw}).execute()


def run_calendar_reaction(credentials: Credentials, config: dict):
    calendar = build("calendar", "v3", credentials=credentials)
    event = {
        "summary": config.get("title", "Nouvel évènement"),
        "start": {"date": config.get("start_date")},
        "end": {"date": config.get("end_date")},
    }
    calendar.events().insert(calendarId="primary", body=event).execute()


def run_applets_for_user(db: Session, user_id: int) -> list[dict]:
    applets = (
        db.query(models.Applet)
        .filter(models.Applet.user_id == user_id, models.Applet.is_active.is_(True))
        .all()
    )
    if not applets:
        return []

    user_email = db.query(models.User.email).filter(models.User.id == user_id).scalar() or ""

    try:
        credentials = get_google_credentials(db, user_id)
    except Exception as exc:
        message = normalize_error_message(str(exc))
        results = []
        for applet in applets:
            log_applet(db, user_id, applet.id, "error", message)
            results.append({"id": applet.id, "status": "error"})
        return results

    results = []
    for applet in applets:
        action_config = json.loads(applet.action_config or "{}")
        reaction_config = json.loads(applet.reaction_config or "{}")
        try:
            action_payload = None
            if applet.action_choice == "gmail_new_mail":
                action_payload = run_gmail_action(credentials, applet, db, action_config)
            if applet.action_choice == "agenda_new_event":
                action_payload = run_calendar_action(credentials, applet, db, action_config)

            if not action_payload:
                log_applet(db, user_id, applet.id, "skipped", "Aucune nouvelle action")
                results.append({"id": applet.id, "status": "skipped"})
                continue

            if applet.reaction_choice == "gmail_send_mail":
                if not reaction_config.get("to") and action_payload.get("from"):
                    reaction_config["to"] = extract_email_address(action_payload["from"])
                if not reaction_config.get("to") and user_email:
                    reaction_config["to"] = user_email
                if not reaction_config.get("subject") and action_payload.get("subject"):
                    reaction_config["subject"] = f"RE: {action_payload['subject']}"
                if not reaction_config.get("message"):
                    reaction_config["message"] = "Message automatique envoyé par AREA."
                if not reaction_config.get("to"):
                    raise HTTPException(status_code=400, detail="La réaction Gmail nécessite un destinataire")
                run_gmail_reaction(credentials, reaction_config)
                if action_payload.get("message_id"):
                    try:
                        mark_gmail_read(credentials, action_payload["message_id"])
                    except Exception:
                        pass
            if applet.reaction_choice == "agenda_create_event":
                run_calendar_reaction(credentials, reaction_config)

            marker = action_payload.get("message_id") or action_payload.get("event_id")
            if marker:
                applet.last_action_marker = str(marker)
                db.commit()

            log_applet(db, user_id, applet.id, "success", "Réaction exécutée")
            results.append({"id": applet.id, "status": "success"})
        except Exception as exc:
            detail = exc.detail if isinstance(exc, HTTPException) else str(exc)
            log_applet(db, user_id, applet.id, "error", normalize_error_message(detail))
            results.append({"id": applet.id, "status": "error"})
    return results


@router.post("/run")
def run_applets(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    results = run_applets_for_user(db, current_user.id)
    return {"results": results}
