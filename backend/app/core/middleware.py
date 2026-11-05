"""Request limits and response security headers."""

import re
from fastapi import Request
from fastapi.responses import JSONResponse
from app.core.config import ORIGINS
from starlette.middleware.gzip import GZipMiddleware


class PublicCompression:
    """Compress public payloads; keep authentication and AI streams untouched."""

    def __init__(self, app):
        self.app = app
        self.compressed = GZipMiddleware(app, minimum_size=1000, compresslevel=5)

    async def __call__(self, scope, receive, send):
        path = scope.get("path", "")
        public = path.startswith("/assets/") or path in {
            "/api/v1/diseases", "/api/v1/library/search", "/api/v1/symptoms",
        }
        target = self.compressed if scope["type"] == "http" and public else self.app
        await target(scope, receive, send)


class BoundedBody:
    """Enforce size before multipart parsing, including chunked requests."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] in {"GET", "HEAD", "OPTIONS"}:
            return await self.app(scope, receive, send)
        chunks, total = [], 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            total += len(chunk)
            if total > 6 * 1024 * 1024:
                return await JSONResponse({"detail": "Yêu cầu quá lớn."}, status_code=413)(
                    scope, receive, send
                )
            chunks.append(chunk)
            if not message.get("more_body", False):
                break
        body, consumed = b"".join(chunks), False

        async def bounded_receive():
            nonlocal consumed
            if not consumed:
                consumed = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        await self.app(scope, bounded_receive, send)


async def safeguards(request: Request, call_next):
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("origin")
        if origin and origin not in ORIGINS:
            return JSONResponse({"detail": "Nguồn yêu cầu không được phép."}, status_code=403)
        length = request.headers.get("content-length")
        if length and (not length.isdigit() or int(length) > 6 * 1024 * 1024):
            return JSONResponse({"detail": "Yêu cầu quá lớn."}, status_code=413)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if request.url.path.startswith("/api"):
        response.headers["Cache-Control"] = "no-store"
    else:
        # Vite fingerprints these files; revised builds get different URLs.
        # Clinical images and HTML must still revalidate after updates.
        if response.status_code == 200 and request.url.path.startswith("/assets/") and re.search(
            r"-[A-Za-z0-9_-]{8,}\.(?:js|css|woff2?)$", request.url.path
        ):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        else:
            response.headers["Cache-Control"] = "no-cache"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' blob: data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
    return response
