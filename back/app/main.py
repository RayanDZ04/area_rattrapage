import os
from pathlib import Path
import asyncio
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from starlette.responses import Response
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
from sqlalchemy import text

from .database import Base, engine, SessionLocal
from . import models
from .routers import auth, applets

ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=True)

app = FastAPI(title="AREA IFTT Basic API")

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", os.getenv("SECRET_KEY", "dev-session-secret")),
    same_site="lax",
    https_only=False,
    session_cookie="area_session",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1|0\.0\.0\.0)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
def root(request: Request):
        accept = (request.headers.get("accept") or "").lower()
        if "text/html" in accept:
                return HTMLResponse(
                        """
                        <!doctype html>
                        <html lang="en">
                            <head>
                                <meta charset="utf-8" />
                                <meta name="viewport" content="width=device-width, initial-scale=1" />
                                <title>AREA API</title>
                            </head>
                            <body>
                                <h1>AREA IFTTT Basic API</h1>
                                <ul>
                                    <li><a href="/docs">Swagger UI</a></li>
                                    <li><a href="/redoc">ReDoc</a></li>
                                    <li><a href="/openapi.json">OpenAPI JSON</a></li>
                                    <li><a href="/health">Health check</a></li>
                                </ul>
                            </body>
                        </html>
                        """.strip()
                )
        return {"name": app.title, "docs": "/docs", "health": "/health"}


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
        return Response(status_code=204)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        columns = conn.execute(text("PRAGMA table_info(users)")).fetchall()
        if columns:
            for col in columns:
                if col[1] == "hashed_password" and col[3] == 1:
                    conn.execute(
                        text(
                            """
                            CREATE TABLE users_new (
                                id INTEGER PRIMARY KEY,
                                first_name VARCHAR(80) NOT NULL,
                                last_name VARCHAR(80) NOT NULL,
                                email VARCHAR(255) NOT NULL,
                                hashed_password VARCHAR(255),
                                created_at DATETIME
                            )
                            """
                        )
                    )
                    conn.execute(
                        text(
                            """
                            INSERT INTO users_new (id, first_name, last_name, email, hashed_password, created_at)
                            SELECT id, first_name, last_name, email, hashed_password, created_at FROM users
                            """
                        )
                    )
                    conn.execute(text("DROP TABLE users"))
                    conn.execute(text("ALTER TABLE users_new RENAME TO users"))
                    conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email)"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_users_id ON users (id)"))
                    break
        applet_cols = conn.execute(text("PRAGMA table_info(applets)")).fetchall()
        if applet_cols:
            existing = {col[1] for col in applet_cols}
            if "action_config" not in existing:
                conn.execute(text("ALTER TABLE applets ADD COLUMN action_config TEXT DEFAULT '{}'"))
            if "reaction_config" not in existing:
                conn.execute(text("ALTER TABLE applets ADD COLUMN reaction_config TEXT DEFAULT '{}'"))
            if "is_active" not in existing:
                conn.execute(text("ALTER TABLE applets ADD COLUMN is_active INTEGER DEFAULT 1"))
            if "last_action_marker" not in existing:
                conn.execute(text("ALTER TABLE applets ADD COLUMN last_action_marker VARCHAR(255)"))
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS applet_logs (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    applet_id INTEGER NOT NULL,
                    status VARCHAR(20) NOT NULL,
                    message VARCHAR(255) NOT NULL,
                    created_at DATETIME
                )
                """
            )
        )
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_applet_logs_user_id ON applet_logs (user_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_applet_logs_applet_id ON applet_logs (applet_id)"))

    asyncio.create_task(run_applets_scheduler())


async def run_applets_scheduler():
    while True:
        await asyncio.sleep(30)
        db = SessionLocal()
        try:
            user_ids = [row[0] for row in db.query(models.Applet.user_id).distinct().all()]
            for user_id in user_ids:
                try:
                    applets.run_applets_for_user(db, user_id)
                except Exception:
                    continue
        finally:
            db.close()


app.include_router(auth.router)
app.include_router(applets.router)
