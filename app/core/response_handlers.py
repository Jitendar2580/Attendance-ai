"""Reusable response handlers for consistent template and form responses."""
from typing import Any, Dict

from fastapi import status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from urllib.parse import quote_plus


class ResponseHandler:
    """Centralized component for handling template and redirect responses."""

    def __init__(self, templates: Jinja2Templates):
        self.templates = templates

    def template_response(
        self,
        request: Any,
        template_name: str,
        context: Dict[str, Any] | None = None,
        status_code: int = 200,
    ):
        """Render template response with request and context."""
        if context is None:
            context = {}
        context["request"] = request
        return self.templates.TemplateResponse(
            template_name,
            context,
            status_code=status_code,
        )

    def template_error(
        self,
        request: Any,
        template_name: str,
        error: str,
        context: Dict[str, Any] | None = None,
    ):
        """Render template response with error message."""
        if context is None:
            context = {}
        context["error"] = error
        return self.template_response(
            request,
            template_name,
            context,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    def redirect_success(self, message: str, redirect_url: str = None) -> RedirectResponse:
        """Redirect with success message."""
        if redirect_url is None:
            redirect_url = "/"
        return RedirectResponse(
            url=f"{redirect_url}?msg={quote_plus(message)}&type=success",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    def redirect_error(self, message: str, redirect_url: str = None) -> RedirectResponse:
        """Redirect with error message."""
        if redirect_url is None:
            redirect_url = "/"
        return RedirectResponse(
            url=f"{redirect_url}?msg={quote_plus(message)}&type=error",
            status_code=status.HTTP_303_SEE_OTHER,
        )
