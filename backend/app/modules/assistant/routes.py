"""Knowledge HTTP endpoints."""

import re
from fastapi import APIRouter, Depends, Request, HTTPException
from app.modules.library.identifiers import find_record
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database.connection import get_db, Disease, DiseaseSymptom, MedicalDocument, Symptom
from app.database.models import DocumentVersion
from app.core.security import rate_limit
from app.modules.library.documents import serialize_document
from app.modules.assistant.knowledge import extract_symptoms, retrieve
from app.core.schemas import QuestionInput, ChatInput
from app.modules.library.catalog import normalize
from app.modules.assistant.chat import generate_answer
from app.modules.assistant.external import external_answer
from app.modules.library.specialties import supports_photo

router = APIRouter()


def conversational_message(text):
    value = normalize(text).strip(" .,!?:;☺😊")
    return bool(re.fullmatch(
        r"(?:hi+|(?:hi){2,}|hello|hey|alo|xin chao|chao(?: ban)?|cam on(?: ban)?|"
        r"thanks?|thank you|ok(?:ay)?|tam biet|bye|haha|hihi|ban la ai|ban lam duoc gi)", value
    ))


def followup_message(text):
    value = normalize(text)
    return bool(re.search(
        r"\b(?:benh do|benh nay|no co|dieu do|ket qua anh|anh nay|co lay|phong ngua|"
        r"trieu chung|nguyen nhan|can luu y|tom tat lai|noi ro hon|giai thich ro hon|"
        r"toi can biet them|cho vi du)\b", value
    ))


@router.post("/api/v1/chat")
def chat_question(body: ChatInput, request: Request, db: Session = Depends(get_db)):
    rate_limit(request, "chat", 10)
    history = [m.model_dump() for m in body.history]
    result = {"status": "general", "passages": [], "message": "Trò chuyện cùng trợ lý AI."}
    social = conversational_message(body.question)
    image_context = body.image_context.model_dump() if body.image_context and not social else None
    if not social:
        from sqlalchemy.orm import load_only
        published = list(db.scalars(select(Disease).options(
            load_only(Disease.id, Disease.name, Disease.english_name)
        ).where(Disease.published == True)))

        def named_topics(value):
            value = normalize(value)
            return [t.id for t in published if any(
                re.search(r"(?<!\w)" + re.escape(normalize(name)) + r"(?!\w)", value)
                for name in [t.name, t.english_name] if len(name) > 2
            )]

        current = named_topics(body.question)
        prior = []
        if followup_message(body.question):
            for turn in reversed(body.history):
                if turn.role == "user":
                    prior = named_topics(turn.content)
                    if prior:
                        break
        image_topics = []
        if body.image_context and followup_message(body.question):
            for value in body.image_context.disease_ids:
                topic = find_record(db, Disease, value)
                if topic and topic.published and supports_photo(topic):
                    image_topics.append(topic.id)
        focus = current or image_topics or prior
        medical = bool(focus or extract_symptoms(body.question)["symptoms"] or re.search(
            r"\b(?:benh|suc khoe|trieu chung|bac si|dau|sot|thuoc|chan doan|dieu tri|"
            r"dinh duong|y te|phong ngua|kham|ket qua anh)\b", normalize(body.question)
        ))
        if body.image_context and followup_message(body.question) and not current and not image_topics and not body.allow_external_ai:
            return {"status": "insufficient_evidence", "passages": [],
                    "method": "image-context-unavailable",
                    "message": "Kết quả ảnh chưa có chủ đề bệnh lý được xác nhận trong thư viện.",
                    "reply": "Ảnh này chưa có kết quả đủ cơ sở để giải thích theo một bệnh cụ thể. Bạn có thể mô tả điều đang lo lắng; tôi sẽ giúp tìm hiểu thêm và gợi ý khi nào nên đi khám."}
        if medical:
            names = [t.name for t in published if t.id in focus]
            query = " ".join(names + [body.question])[:300]
            evidence = retrieve_answer(QuestionInput(question=query), request, db,
                                       focus_ids=focus, allow_personal=True)
            result.update(passages=evidence["passages"])
            if evidence["passages"]:
                result.update(status="supported", message="Có bài viết tham khảo trong thư viện.")
    result["reply"] = generate_answer(body.question, result["passages"], history, image_context)
    result["method"] = "bm25-extractive-v1"
    if not social and not result["passages"]:
        result.update(status="insufficient_evidence", message="Chưa tìm thấy tài liệu phù hợp trong thư viện.")
        if body.allow_external_ai:
            try:
                rate_limit(request, 'chat-gemini', 5)
                return external_answer(body.question, history, image_context)
            except HTTPException as error:
                result['fallback'] = {'status': 'unavailable', 'message': str(error.detail)}
    return result


@router.post("/api/v1/nlp/parse")
def parse_question(body: QuestionInput, request: Request, db: Session = Depends(get_db)):
    rate_limit(request, "nlp", 30)
    parsed = extract_symptoms(body.question)
    for symptom in parsed["symptoms"]:
        row = find_record(db, Symptom, symptom["id"])
        symptom["id"] = row.id if row else symptom["id"]
    return parsed


@router.post("/api/v1/answers")
def answer_question(body: QuestionInput, request: Request, db: Session = Depends(get_db)):
    return retrieve_answer(body, request, db)


def retrieve_answer(body, request, db, *, focus_ids=None, allow_personal=False):
    rate_limit(request, "answers", 30)
    normalized = normalize(body.question)
    sensitive_intent = re.search(
        r"\b(?:chan doan|ke don|lieu dung|uong thuoc gi|toi bi benh gi|toi mac benh gi|toi co bi|toi co phai|dieu tri cho toi)\b|\b(?:toi|em)\b.*\b(?:co phai|benh gi|mac benh)\b",
        normalized,
    )
    if sensitive_intent and not allow_personal:
        return {
            "status": "out_of_scope",
            "method": "bm25-extractive-v1",
            "passages": [],
            "message": "Câu hỏi yêu cầu kết luận hoặc điều trị cá nhân nằm ngoài phạm vi thư viện. Bạn có thể hỏi thông tin tổng quan về một chủ đề.",
        }
    query = (
        select(MedicalDocument, DocumentVersion, Disease)
        .join(Disease, Disease.id == MedicalDocument.disease_id)
        .join(DocumentVersion, (DocumentVersion.document_id == MedicalDocument.id)
              & (DocumentVersion.version == MedicalDocument.version))
        .where(MedicalDocument.published == True, Disease.published == True)
    )
    if focus_ids:
        query = query.where(Disease.id.in_(focus_ids))
    docs = db.execute(query).all()
    eligible = select(MedicalDocument.disease_id).where(
        MedicalDocument.published == True, MedicalDocument.disease_id.in_(
            select(Disease.id).where(Disease.published == True)
        )
    )
    if focus_ids:
        eligible = eligible.where(MedicalDocument.disease_id.in_(focus_ids))
    symptoms_by_disease = {}
    for disease_id, slug in db.execute(
        select(DiseaseSymptom.disease_id, Symptom.slug)
        .join(Symptom, Symptom.id == DiseaseSymptom.symptom_id)
        .where(DiseaseSymptom.disease_id.in_(eligible))
    ):
        symptoms_by_disease.setdefault(disease_id, []).append(slug)
    corpus = []
    for doc, version, disease in docs:
        corpus.append(
            {
                "document_id": doc.id,
                "document_version": doc.version,
                "title": doc.title,
                "content": version.content,
                "checksum": version.checksum,
                "publisher": doc.publisher,
                "source_url": doc.source_url,
                "usage_note": doc.usage_note,
                "disease_id": doc.disease_id,
                "disease_name": disease.name,
                "symptom_ids": symptoms_by_disease.get(disease.id, []),
            }
        )
    found = retrieve(body.question, corpus)
    passages = [{k: v for k, v in entry.items() if k != "symptom_ids"} for entry in found]
    return {
        "status": "supported" if passages else "insufficient_evidence",
        "method": "bm25-extractive-v1",
        "message": (
            "Các đoạn tham khảo liên quan, giữ nguyên từ kho nội dung; chưa thẩm định lâm sàng."
            if passages
            else "Kho tài liệu hiện chưa có đủ nội dung liên quan. Thử câu hỏi về một chủ đề trong thư viện."
        ),
        "passages": passages,
    }


@router.get("/api/v1/documents")
def public_documents(db: Session = Depends(get_db)):
    docs = db.scalars(
        select(MedicalDocument)
        .join(Disease)
        .where(MedicalDocument.published == True, Disease.published == True)
        .order_by(MedicalDocument.title)
    )
    return [serialize_document(doc, db) for doc in docs]
