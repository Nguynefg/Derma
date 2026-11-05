"""Source-grounded retrieval and conservative Vietnamese term parsing.

This is a lexical BM25 baseline and extractive answers, not a generative LLM.
No internet fetch is performed and document text is never executed.
"""

import math
import re
import unicodedata
from collections import Counter


def normalize(text):
    text = text.lower().replace("đ", "d")
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


ALIASES = {
    "nail-change": ["móng đổi màu", "móng dày", "móng giòn"],
    "swelling": ["sưng da", "da sưng"],
    "pus": ["chảy mủ", "rỉ mủ"],
    "dark-patches": ["mảng da sẫm màu", "da sẫm màu"],
    "excessive-sweat": ["ra mồ hôi nhiều", "đổ mồ hôi nhiều"],
    "mole-change": ["nốt ruồi thay đổi", "nốt ruồi đổi màu", "nốt ruồi lớn lên"],
    "sores": ["vết loét", "trợt da"],
    "blisters": ["mụn nước", "bọng nước"],
    "pain": ["đau da"],
    "crust": ["vảy tiết", "đóng vảy tiết"],
    "rough": ["sần ráp", "da sần"],
    "wheals": ["sẩn phù", "mảng nổi"],
    "itch": ["ngứa", "ngứa ngáy"],
    "redness": ["đỏ da", "da đỏ", "đỏ mặt"],
    "scale": ["bong vảy", "tróc vảy", "tróc da", "bong da"],
    "bumps": ["mụn", "nổi sẩn"],
    "dry": ["da khô", "khô da", "nứt da"],
    "burning": ["nóng rát", "rát da"],
    "white-patches": ["mảng trắng", "mất màu da", "mất sắc tố"],
    "hair-loss": ["rụng tóc", "rụng tóc từng mảng"],
}
NAMES = {
    "nail-change": "Móng đổi màu / dày / giòn",
    "swelling": "Sưng da",
    "pus": "Chảy mủ",
    "dark-patches": "Mảng da sẫm màu",
    "excessive-sweat": "Ra mồ hôi nhiều",
    "mole-change": "Nốt ruồi thay đổi",
    "sores": "Vết loét / trợt da",
    "blisters": "Mụn nước",
    "pain": "Đau da",
    "crust": "Đóng vảy tiết",
    "rough": "Da sần ráp",
    "wheals": "Sẩn phù / mảng nổi",
    "itch": "Ngứa",
    "redness": "Đỏ da",
    "scale": "Bong vảy",
    "bumps": "Sẩn / mụn",
    "dry": "Da khô, nứt",
    "burning": "Nóng rát",
    "white-patches": "Mảng da mất màu",
    "hair-loss": "Rụng tóc từng mảng",
}


from app.data.library_dermnet import SYMPTOMS as NEW_SYMPTOMS

NAMES.update(NEW_SYMPTOMS)
from app.data.library_general import SYMPTOMS as GENERAL_SYMPTOMS

NAMES.update(GENERAL_SYMPTOMS)
ALIASES.update({code: [name.lower()] for code, name in GENERAL_SYMPTOMS.items()})
ALIASES.update(
    {
        "heartburn": ["ợ nóng", "trào ngược"],
        "nausea": ["buồn nôn", "nôn"],
        "palpitations": ["hồi hộp", "tim đập nhanh"],
        "numbness": ["tê", "giảm cảm giác"],
        "nasal-blockage": ["nghẹt mũi", "chảy mũi"],
        "weight-loss": ["sụt cân", "sụt cân không chủ ý"],
    }
)
ALIASES.update({code: [name.lower()] for code, name in NEW_SYMPTOMS.items()})
ALIASES.update(
    {
        "comedones": ["mụn đầu đen", "mụn đầu trắng"],
        "nodules": ["cục dưới da", "nốt dưới da"],
        "purple-spots": ["chấm tím đỏ", "mảng tím đỏ", "ban xuất huyết"],
        "bleeding": ["tổn thương chảy máu", "dễ chảy máu"],
        "thick-skin": ["da dày", "lichen hóa"],
        "diffuse-hair-loss": ["tóc thưa", "rụng tóc lan tỏa"],
        "broken-hair": ["tóc gãy", "tóc gãy sát da đầu"],
        "nail-pitting": ["móng có chấm lõm", "móng lõm"],
        "nail-separation": ["móng tách", "móng tách khỏi nền móng"],
        "skin-hardening": ["da cứng", "da căng cứng"],
    }
)


def extract_symptoms(text):
    original = unicodedata.normalize("NFC", text).lower()
    normalized = normalize(original)
    # Clause boundaries avoid spreading a negation into a following positive clause.
    clauses = re.split(r"[,;.!?\n]|\b(?:nhưng|nhung|tuy nhiên|tuy nhien|còn|con|và|va)\b", original)
    matches = []
    third_person = bool(
        re.search(r"\b(?:con toi|me toi|bo toi|ban toi|nguoi khac|em be)\b", normalized)
    )
    for symptom_id, aliases in ALIASES.items():
        mentions = []
        for clause in clauses:
            normalized_clause = normalize(clause)
            for alias in sorted(aliases, key=len, reverse=True):
                term = normalize(alias)
                for m in re.finditer(r"(?<!\w)" + re.escape(term) + r"(?!\w)", normalized_clause):
                    raw_match = clause[m.start() : m.end()]
                    # Preserve accented distinctions: "ngựa" must not become "ngứa".
                    # Unaccented input is accepted only as a suggestion to confirm.
                    if normalize(raw_match) != raw_match and raw_match != alias.lower():
                        continue
                    preceding = normalized_clause[: m.start()]
                    # Uncertainty overrides direct negation ("không biết có ngứa không").
                    if re.search(
                        r"\b(?:khong biet|chua ro|co the|khong chac|lieu|neu)\b", normalized_clause
                    ):
                        presence = "unknown"
                    elif re.search(r"\b(?:khong|chua|het)\b(?:\s+\w+){0,3}\s*$", preceding):
                        presence = "absent"
                    else:
                        presence = "present"
                    mentions.append(presence)
        if mentions:
            distinct = set(mentions)
            presence = mentions[0] if len(distinct) == 1 else "unknown"
            if third_person:
                presence = "unknown"
            matches.append(
                {
                    "id": symptom_id,
                    "name": NAMES[symptom_id],
                    "presence": presence,
                    "requires_confirmation": True,
                }
            )
    return {
        "symptoms": matches,
        "third_person": third_person,
        "notice": "Đây là nhận diện thuật ngữ bằng quy tắc. Hãy xác nhận từng dấu hiệu trước khi tra cứu.",
    }


STOPWORDS = set(
    "toi ban la va cua co bi mot nhung gi thi khi cho ve voi duoc hay nhu nao khong xin vui long".split()
)


def tokens(text):
    return [t for t in re.findall(r"[a-z0-9]+", normalize(text)) if t not in STOPWORDS]


def retrieve(question, entries, top_k=3):
    """BM25 with exact symptom-term expansion. Returns original text and provenance."""
    query_tokens = tokens(question)
    parsed = extract_symptoms(question)
    for symptom in parsed["symptoms"]:
        if symptom["presence"] == "present":
            query_tokens.extend(tokens(symptom["name"]))
    query_tokens = list(dict.fromkeys(query_tokens))
    if not query_tokens or not entries:
        return []
    corpus = [Counter(tokens(e["title"] + " " + e["content"])) for e in entries]
    length = [sum(c.values()) for c in corpus]
    average_length = sum(length) / max(1, len(length)) or 1
    frequency = Counter(t for document in corpus for t in document)
    scored = []
    for index, document in enumerate(corpus):
        score, overlap = 0.0, []
        for token in query_tokens:
            tf = document.get(token, 0)
            if not tf:
                continue
            overlap.append(token)
            idf = math.log(1 + (len(corpus) - frequency[token] + 0.5) / (frequency[token] + 0.5))
            score += idf * tf * 2.2 / (tf + 1.2 * (0.25 + 0.75 * length[index] / average_length))
        # Require substantive lexical evidence; a single incidental word is not enough.
        disease_name = tokens(entries[index]["disease_name"])
        exact_name = bool(disease_name and all(t in query_tokens for t in disease_name))
        symptom_match = any(
            s["presence"] == "present" and s["id"] in entries[index]["symptom_ids"]
            for s in parsed["symptoms"]
        )
        if score > 0 and (exact_name or symptom_match or len(set(overlap)) >= 2):
            scored.append(
                {**entries[index], "score": round(score, 4), "matched_terms": sorted(set(overlap))}
            )
    scored.sort(key=lambda e: (-e["score"], e["document_id"]))
    return scored[:top_k]
