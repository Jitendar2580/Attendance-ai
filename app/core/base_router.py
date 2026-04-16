"""Base router component for consistent route initialization and setup."""
from fastapi import APIRouter
from fastapi.templating import Jinja2Templates
import os

from app.core.response_handlers import ResponseHandler


class BaseRouter:
    """Base component for route setup with common utilities."""

    def __init__(self, prefix: str, tags: list[str] = None):
        self.router = APIRouter(prefix=prefix, tags=tags or [])
        self.templates = Jinja2Templates(directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"))
        self.response_handler = ResponseHandler(self.templates)

    def get_router(self) -> APIRouter:
        """Return the configured router."""
        return self.router
