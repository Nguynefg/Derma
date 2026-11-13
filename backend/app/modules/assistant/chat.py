"""Local extractive replies; no external service or language model is called."""
import re
from app.modules.assistant.knowledge import normalize


def generate_answer(question: str, passages: list[dict], history=None, image_context=None) -> str:
    value = normalize(question).strip(" .,!?:;")
    if re.fullmatch(r"(?:cam on(?: ban)?|thanks?|thank you)", value):
        return "Rất vui được hỗ trợ bạn. Bạn muốn tìm hiểu thêm chủ đề sức khỏe nào?"
    if re.fullmatch(r"(?:hi+|(?:hi){2,}|hello|hey|alo|xin chao|chao(?: ban)?|hihi|haha|ban la ai|ban lam duoc gi)", value):
        return "Chào bạn! Tôi hỗ trợ tra cứu tài liệu sức khỏe trong thư viện. Bạn có thể hỏi tên bệnh, dấu hiệu hoặc cách phòng ngừa."
    if re.fullmatch(r"(?:ok(?:ay)?|tam biet|bye)", value):
        return "Bạn có thể tiếp tục tra cứu bất cứ khi nào cần."
    if not passages:
        return "Chưa tìm thấy đoạn tài liệu phù hợp trong thư viện. Bạn hãy nêu tên bệnh hoặc dấu hiệu cụ thể hơn."
    excerpts = [f"{p['disease_name']} [{i}]\n{p['content']}"
                for i, p in enumerate(passages[:4], start=1)]
    return "Thông tin trích từ tài liệu trong thư viện:\n\n" + "\n\n".join(excerpts)
