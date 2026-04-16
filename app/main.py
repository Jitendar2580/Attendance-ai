from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import get_settings
from app.core.init import initialize_defaults
from app.models.base import Base
from app.core.database import engine
from app.routes import attendance, auth, chat, dashboard, profile, teams, users

settings = get_settings()

app = FastAPI(title=settings.app_name)

# Middleware setup
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    session_cookie=settings.session_cookie_name,
    https_only=False,
    same_site="lax",
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Router includes
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(attendance.router)
app.include_router(profile.router)
app.include_router(users.router)
app.include_router(teams.router)
app.include_router(chat.router)


@app.get("/")
def index(request: Request):
    """Root endpoint - redirect to dashboard if authenticated, else to login."""
    if request.session.get("user_id"):
        return RedirectResponse(url="/dashboard", status_code=303)
    return RedirectResponse(url="/auth/login", status_code=303)


@app.on_event("startup")
def startup() -> None:
    """Initialize database and defaults on application startup."""
    Base.metadata.create_all(bind=engine)
    initialize_defaults()
