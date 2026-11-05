from fastapi import FastAPI
from fastapi.responses import PlainTextResponse, StreamingResponse
from fastapi.testclient import TestClient

from app.core.middleware import PublicCompression, safeguards


def test_public_compression_preserves_payload_and_excludes_private_responses():
    app = FastAPI()
    app.add_middleware(PublicCompression)
    payload = {"items": ["Thông tin sức khỏe"] * 500}

    @app.get("/api/v1/diseases")
    @app.get("/api/v1/auth/me")
    def data():
        return payload

    with TestClient(app) as client:
        public = client.get("/api/v1/diseases", headers={"Accept-Encoding": "gzip"})
        assert public.json() == payload
        assert public.headers["content-encoding"] == "gzip"
        assert int(public.headers["content-length"]) < len(public.content) / 2
        private = client.get("/api/v1/auth/me", headers={"Accept-Encoding": "gzip"})
        assert "content-encoding" not in private.headers


def test_only_successful_fingerprinted_assets_get_long_cache():
    app = FastAPI()
    app.middleware("http")(safeguards)

    @app.get("/{path:path}")
    def data(path: str):
        return PlainTextResponse("example", status_code=404 if "missing" in path else 200)

    with TestClient(app) as client:
        assert "immutable" in client.get("/assets/index-Ab1234_z.js").headers["cache-control"]
        for path in ["/", "/assets/library/diseases/cover.webp", "/assets/missing-Ab1234_z.js"]:
            assert client.get(path).headers["cache-control"] == "no-cache"
        assert client.get("/api/v1/auth/me").headers["cache-control"] == "no-store"


def test_ai_stream_is_not_compressed():
    app = FastAPI()
    app.add_middleware(PublicCompression)

    @app.get("/api/v1/assistant/stream")
    def stream():
        return StreamingResponse(iter(["data: hello\n\n"] * 100), media_type="text/event-stream")

    with TestClient(app) as client:
        response = client.get("/api/v1/assistant/stream", headers={"Accept-Encoding": "gzip"})
        assert "content-encoding" not in response.headers
        assert response.text.startswith("data: hello")
