import os
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt
from authlib.integrations.starlette_client import OAuth
from authlib.integrations.base_client.errors import MismatchingStateError, OAuthError
import httpx
from dotenv import load_dotenv
from sqlalchemy.orm import Session

from ..database import SessionLocal
from .. import models, schemas
from ..security import hash_password, verify_password, create_access_token, SECRET_KEY, ALGORITHM

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer()

load_dotenv(override=True)


def get_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    return value.strip()

oauth = OAuth()
oauth.register(
    name="google",
    client_id=get_env("GOOGLE_CLIENT_ID"),
    client_secret=get_env("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={
        "scope": "openid email profile https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.modify https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/calendar.readonly https://www.googleapis.com/auth/calendar.events",
        "token_endpoint_auth_method": "client_secret_post",
    },
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Token invalide") from exc

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Utilisateur introuvable")
    return user


@router.post("/register", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    if len(payload.password) > 72:
        raise HTTPException(status_code=400, detail="Mot de passe trop long (max 72 caractères)")

    existing = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email déjà enregistré")

    user = models.User(
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=schemas.Token)
def login(payload: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user or not user.hashed_password:
        raise HTTPException(status_code=401, detail="Identifiants invalides")
    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Identifiants invalides")

    token = create_access_token(subject=str(user.id))
    return {"access_token": token, "token_type": "bearer", "user": user}


@router.get("/me", response_model=schemas.UserOut)
def me(current_user: models.User = Depends(get_current_user)):
    return current_user


@router.get("/google/login")
async def google_login(request: Request):
    request.session.clear()
    backend_url = os.getenv("BACKEND_URL", "http://localhost:8080").rstrip("/")
    redirect_uri = f"{backend_url}/auth/google/callback"
    return await oauth.google.authorize_redirect(
        request,
        redirect_uri,
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
    )


@router.get("/google/debug")
def google_debug():
    backend_url = os.getenv("BACKEND_URL", "http://localhost:8080").rstrip("/")
    secret = get_env("GOOGLE_CLIENT_SECRET") or ""
    client_secret = oauth.google.client_secret or ""
    return {
        "google_client_id": get_env("GOOGLE_CLIENT_ID"),
        "google_client_secret_set": bool(secret),
        "google_client_secret_len": len(secret),
        "oauth_client_id": oauth.google.client_id,
        "oauth_client_secret_set": bool(client_secret),
        "oauth_client_secret_len": len(client_secret),
        "oauth_token_auth_method": oauth.google.client_kwargs.get("token_endpoint_auth_method"),
        "backend_url": backend_url,
        "redirect_uri": f"{backend_url}/auth/google/callback",
    }


@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    backend_url = os.getenv("BACKEND_URL", "http://localhost:8080").rstrip("/")
    redirect_uri = f"{backend_url}/auth/google/callback"
    async def manual_exchange(auth_code: str):
        token_endpoint = "https://oauth2.googleapis.com/token"
        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_endpoint,
                data={
                    "code": auth_code,
                    "client_id": get_env("GOOGLE_CLIENT_ID"),
                    "client_secret": get_env("GOOGLE_CLIENT_SECRET"),
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        data = response.json()
        if response.status_code >= 400 or "error" in data:
            error = data.get("error", "oauth_error")
            description = data.get("error_description")
            detail = f"{error}: {description}" if description else error
            raise HTTPException(status_code=400, detail=detail)
        return data

    try:
        token = await oauth.google.authorize_access_token(request)
    except MismatchingStateError:
        code = request.query_params.get("code")
        if not code:
            raise HTTPException(status_code=400, detail="Code d'autorisation manquant")
        token = await manual_exchange(code)
    except OAuthError:
        code = request.query_params.get("code")
        if not code:
            raise HTTPException(status_code=400, detail="Code d'autorisation manquant")
        token = await manual_exchange(code)
    userinfo = token.get("userinfo")
    if not userinfo:
        userinfo = await oauth.google.userinfo(token=token)

    email = userinfo.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email Google indisponible")

    first_name = userinfo.get("given_name") or "User"
    last_name = userinfo.get("family_name") or "Google"

    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        user = models.User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            hashed_password=None,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    refresh_token = token.get("refresh_token")
    if not refresh_token:
        existing_token = (
            db.query(models.ServiceToken)
            .filter(models.ServiceToken.user_id == user.id, models.ServiceToken.provider == "google")
            .order_by(models.ServiceToken.created_at.desc())
            .first()
        )
        if existing_token:
            refresh_token = existing_token.refresh_token

    db.query(models.ServiceToken).filter(
        models.ServiceToken.user_id == user.id,
        models.ServiceToken.provider == "google",
    ).delete()
    service_token = models.ServiceToken(
        user_id=user.id,
        provider="google",
        access_token=token.get("access_token", ""),
        refresh_token=refresh_token,
    )
    db.add(service_token)
    db.commit()

    jwt_token = create_access_token(subject=str(user.id))
    redirect_front = os.getenv("FRONTEND_URL", "http://localhost:5173")
    return_url = f"{redirect_front}/index.html?token={jwt_token}&first_name={user.first_name}"
    return RedirectResponse(url=return_url, status_code=302)


@router.put("/me", response_model=schemas.UserOut)
def update_me(
    payload: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if payload.first_name is not None:
        current_user.first_name = payload.first_name
    if payload.last_name is not None:
        current_user.last_name = payload.last_name

    db.commit()
    db.refresh(current_user)
    return current_user
