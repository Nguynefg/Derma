"""Shared AI REST client. Credentials stay in server-side headers."""

import json
import os
import re
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import urlsplit
from fastapi import HTTPException


def failure_metadata(error, model):
    """Keep useful error classification without returning raw provider payloads."""
    details = {}
    try:
        payload = json.loads(error.read(32768)).get("error", {})
        for item in payload.get("details", []):
            if not isinstance(item, dict):
                continue
            if item.get("@type", "").endswith("RetryInfo"):
                delay = item.get("retryDelay", "")
                if isinstance(delay, str) and re.fullmatch(r"[0-9]+(?:\.[0-9]+)?s", delay):
                    details["retry_after_seconds"] = min(float(delay[:-1]), 3600)
    except (ValueError, TypeError, AttributeError, OSError):
        pass
    return {"upstream_status": error.code, "upstream_model": model, **details}


def generate(
    instructions,
    parts,
    schema=None,
    image=False,
    max_output_tokens=4096,
    timeout=25,
    thinking_level=None,
    grounding=False,
):
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise HTTPException(
            503, "Chưa cấu hình khóa dịch vụ AI trong .env. Thêm key và khởi động lại server."
        )
    model = os.getenv("GEMINI_IMAGE_MODEL", "") if image else os.getenv("GEMINI_CHAT_MODEL", "")
    model = model or os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
    if not re.fullmatch(r"[a-zA-Z0-9._-]+", model):
        raise HTTPException(503, "Tên model AI trong .env không hợp lệ.")
    config = {"maxOutputTokens": max_output_tokens}
    if thinking_level:
        config["thinkingConfig"] = {"thinkingLevel": thinking_level}
    if schema:
        config.update(responseMimeType="application/json", responseJsonSchema=schema)
    payload = {
        "systemInstruction": {"parts": [{"text": instructions}]},
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": config,
    }
    if grounding:
        if schema:
            raise ValueError("Grounded responses must not use a structured response schema")
        payload["tools"] = [{"google_search": {}}]
    request = Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps(payload).encode(),
        headers={"x-goog-api-key": key, "Content-Type": "application/json"},
        method="POST",
    )
    for attempt in range(2):
        try:
            with urlopen(request, timeout=timeout) as response:
                result = json.load(response)
            break
        except HTTPError as error:
            if error.code in {502, 503, 504} and attempt == 0:
                error.close()
                time.sleep(1)
                continue
            metadata = failure_metadata(error, model)
            error.close()
            messages = {
                400: "Dịch vụ phân tích từ chối yêu cầu. Cần kiểm tra cấu hình trên máy chủ.",
                401: "Khóa dịch vụ AI không hợp lệ. Cần cập nhật cấu hình máy chủ.",
                403: "Dịch vụ AI từ chối truy cập. Cần kiểm tra quyền truy cập.",
                404: "Model phân tích đã cấu hình không còn khả dụng.",
                429: "Google đang chặn yêu cầu do hạn mức hoặc giới hạn lượt gọi; chưa xác định được hạn mức cụ thể.",
                503: "Dịch vụ AI đang bận. Vui lòng thử lại sau ít phút.",
            }
            failure = HTTPException(
                502,
                messages.get(
                    error.code, "Dịch vụ phân tích tạm thời gặp lỗi. Vui lòng thử lại sau."
                ),
            )
            for name, value in metadata.items():
                setattr(failure, name, value)
            raise failure from None
        except (URLError, TimeoutError) as error:
            if attempt == 0:
                time.sleep(1)
                continue
            timed_out = isinstance(error, TimeoutError) or isinstance(getattr(error, "reason", None), TimeoutError)
            failure = HTTPException(502, (
                "Dịch vụ AI chưa phản hồi trong thời gian chờ. Chưa thể kết luận do hết hạn mức."
                if timed_out else "Kết nối tới dịch vụ AI bị gián đoạn. Vui lòng thử lại sau."
            ))
            failure.upstream_model = model
            failure.error_kind = "timeout" if timed_out else "network"
            raise failure from None
        except ValueError:
            raise HTTPException(
                502, "Không nhận được phản hồi hợp lệ từ dịch vụ AI. Vui lòng thử lại."
            ) from None
    candidates = result.get("candidates", []) if isinstance(result, dict) else []
    if not isinstance(candidates, list) or not candidates or not isinstance(candidates[0], dict) or candidates[0].get("finishReason") != "STOP":
        raise HTTPException(502, "AI chưa trả kết quả đầy đủ hoặc từ chối phân tích. Hãy thử lại.")
    text = "\n".join(
        p.get("text", "")
        for p in candidates[0].get("content", {}).get("parts", [])
        if not p.get("thought")
    ).strip()
    if not text:
        raise HTTPException(502, "AI chưa trả nội dung. Hãy thử lại.")
    if grounding:
        metadata = candidates[0].get("groundingMetadata", {})
        if not isinstance(metadata, dict):
            metadata = {}
        sources, seen = [], set()
        chunks = metadata.get("groundingChunks", [])
        for chunk in chunks if isinstance(chunks, list) else []:
            if not isinstance(chunk, dict):
                continue
            web = chunk.get("web", {})
            if not isinstance(web, dict):
                continue
            uri = web.get("uri", "")
            if not isinstance(uri, str):
                continue
            try:
                parsed = urlsplit(uri)
            except ValueError:
                continue
            if (parsed.scheme != "https" or not parsed.hostname or parsed.username
                    or parsed.password or len(uri) > 4096 or uri in seen):
                continue
            seen.add(uri)
            sources.append({"title": str(web.get("title") or parsed.hostname)[:250], "url": uri})
        entry = metadata.get("searchEntryPoint", {})
        rendered = entry.get("renderedContent", "") if isinstance(entry, dict) else ""
        return {"reply": text, "external_sources": sources,
                "search_suggestions_html": rendered if isinstance(rendered, str) and len(rendered) <= 100000 else ""}
    return text
