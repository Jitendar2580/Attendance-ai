from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import get_settings
from app.core.init import initialize_defaults
from app.models.base import Base
from app.core.database import engine
from app.routes import attendance, auth, chat, dashboard, profile, teams, users

settings = get_settings()

ROOT_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = ROOT_DIR / "templates"
STATIC_DIR = ROOT_DIR / "static"

app = FastAPI(title=settings.app_name)
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def not_found_html() -> HTMLResponse:
    """Static 404 page without Jinja (avoids loader/version issues in production)."""
    return HTMLResponse(
        (TEMPLATES_DIR / "404.html").read_text(encoding="utf-8"),
        status_code=404,
    )


# Middleware setup
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    session_cookie=settings.session_cookie_name,
    https_only=False,
    same_site="lax",
)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Exception handlers
@app.exception_handler(StarletteHTTPException)
async def starlette_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 401:
        return RedirectResponse(url="/auth/login", status_code=303)
    elif exc.status_code == 404:
        if request.url.path == "/404.html":
            return not_found_html()
        return RedirectResponse(url="/404.html", status_code=303)
    return HTMLResponse(content=str(exc.detail), status_code=exc.status_code)

@app.get("/404.html")
def not_found_page():
    return not_found_html()

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
