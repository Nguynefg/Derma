"""Shared AI REST client. Credentials stay in server-side headers."""

import json
import os
import re
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from fastapi import HTTPException


def generate(
    instructions,
    parts,
    schema=None,
    image=False,
    max_output_tokens=4096,
    timeout=25,
    thinking_level=None,
):
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise HTTPException(
            503, "Chưa cấu hình khóa dịch vụ AI trong .env. Thêm key và khởi động lại server."
        )
    model = os.getenv("GEMINI_IMAGE_MODEL", "") if image else os.getenv("GEMINI_CHAT_MODEL", "")
    model = model or os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
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
            messages = {
                400: "Dịch vụ phân tích từ chối yêu cầu. Cần kiểm tra cấu hình trên máy chủ.",
                401: "Khóa dịch vụ AI không hợp lệ. Cần cập nhật cấu hình máy chủ.",
                403: "Dịch vụ AI từ chối truy cập. Cần kiểm tra quyền truy cập.",
                404: "Model phân tích đã cấu hình không còn khả dụng.",
                429: "Dịch vụ AI đã hết hạn mức hoặc đang giới hạn lượt gọi. Vui lòng thử lại sau.",
                503: "Dịch vụ AI đang bận. Vui lòng thử lại sau ít phút.",
            }
            failure = HTTPException(
                502,
                messages.get(
                    error.code, "Dịch vụ phân tích tạm thời gặp lỗi. Vui lòng thử lại sau."
                ),
            )
            failure.upstream_status = error.code
            raise failure from None
        except (URLError, TimeoutError):
            if attempt == 0:
                time.sleep(1)
                continue
            raise HTTPException(
                502, "Kết nối tới dịch vụ AI bị gián đoạn. Vui lòng thử lại sau."
            ) from None
        except ValueError:
            raise HTTPException(
                502, "Không nhận được phản hồi hợp lệ từ dịch vụ AI. Vui lòng thử lại."
            ) from None
    candidates = result.get("candidates", [])
    if not candidates or candidates[0].get("finishReason") != "STOP":
        raise HTTPException(502, "AI chưa trả kết quả đầy đủ hoặc từ chối phân tích. Hãy thử lại.")
    text = "\n".join(
        p.get("text", "")
        for p in candidates[0].get("content", {}).get("parts", [])
        if not p.get("thought")
    ).strip()
    if not text:
        raise HTTPException(502, "AI chưa trả nội dung. Hãy thử lại.")
    return text
