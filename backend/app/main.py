"""Entry point for the Roomie API.

Run it from the backend/ folder with:  uvicorn app.main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.logging import REQUEST_ID_HEADER, add_request_logging, configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.environment)

    app = FastAPI(title=settings.app_name, version=__version__)

    register_error_handlers(app)
    add_request_logging(app)

    # Browsers block a page on one address (the frontend, port 3000) from
    # calling an API on another (the backend, port 8000) unless the API
    # explicitly allows that address. Only the listed origins are allowed.
    # Added last so it wraps everything else, including error responses.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        # Lets the browser send the session cookie. This is only safe
        # because the origins above are an explicit list, never "*".
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[REQUEST_ID_HEADER],
    )

    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
