from app.modules.library.library_source import source_data, source_filter
"""Vietnamese display titles; original WHO titles and source JSON stay intact."""

CHAPTER_TITLES_VI = {
    "01": "Một số bệnh nhiễm trùng hoặc ký sinh trùng",
    "02": "Khối u",
    "03": "Bệnh về máu hoặc cơ quan tạo máu",
    "04": "Bệnh hệ miễn dịch",
    "05": "Bệnh nội tiết, dinh dưỡng hoặc chuyển hóa",
    "06": "Rối loạn tâm thần, hành vi hoặc phát triển thần kinh",
    "07": "Rối loạn giấc ngủ và thức",
    "08": "Bệnh hệ thần kinh",
    "09": "Bệnh hệ thị giác",
    "10": "Bệnh tai hoặc xương chũm",
    "11": "Bệnh hệ tuần hoàn",
    "12": "Bệnh hệ hô hấp",
    "13": "Bệnh hệ tiêu hóa",
    "14": "Bệnh da",
    "15": "Bệnh hệ cơ xương khớp hoặc mô liên kết",
    "16": "Bệnh hệ sinh dục và tiết niệu",
    "17": "Các tình trạng liên quan đến sức khỏe tình dục",
    "18": "Thai kỳ, sinh đẻ hoặc hậu sản",
    "19": "Một số tình trạng bắt nguồn từ thời kỳ chu sinh",
    "20": "Bất thường phát triển",
    "21": "Triệu chứng, dấu hiệu hoặc phát hiện lâm sàng chưa được phân loại ở nơi khác",
    "22": "Chấn thương, ngộ độc hoặc một số hậu quả khác do nguyên nhân bên ngoài",
    "23": "Nguyên nhân bên ngoài gây bệnh hoặc tử vong",
    "24": "Các yếu tố ảnh hưởng đến tình trạng sức khỏe hoặc việc tiếp xúc với dịch vụ y tế",
    "25": "Mã dành cho mục đích đặc biệt",
    "26": "Chương bổ sung về các tình trạng theo y học cổ truyền",
    "V": "Phần bổ sung về đánh giá chức năng",
    "X": "Mã mở rộng",
}


def translate_chapter_titles(engine):
    import json
    from sqlalchemy import select, or_
    from sqlalchemy.orm import Session
    from app.database.models import Disease
    from app.modules.library.catalog import normalize

    updated = 0
    with Session(engine) as db, db.begin():
        rows = db.scalars(
            select(Disease).where(
                Disease.review_status == "icd_classification",
                source_filter("class_kind", "chapter"),
            )
        )
        rows = list(rows)
        from app.modules.library.library_editorial import editorials
        manually_edited = editorials(db, [r.id for r in rows])
        for row in rows:
            if row.id in manually_edited:
                continue
            source = source_data(row)
            title = CHAPTER_TITLES_VI.get(source.get("chapter_no"))
            if source.get("class_kind") != "chapter" or not title:
                continue
            aliases = list(row.aliases or [])
            search_alias = normalize(title)
            if row.name != title or title not in aliases or search_alias not in aliases:
                row.name = title
                row.aliases = list(dict.fromkeys([*aliases, title, search_alias]))
                updated += 1
    return {"updated_chapters": updated, "language": "vi"}
