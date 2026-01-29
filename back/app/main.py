import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
from sqlalchemy import text

from .database import Base, engine
from .routers import auth, applets

load_dotenv(override=True)

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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


app.include_router(auth.router)
app.include_router(applets.router)
