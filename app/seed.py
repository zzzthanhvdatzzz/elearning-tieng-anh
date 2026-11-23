"""Seed dữ liệu chạy thử — idempotent, chạy lại không tạo trùng.

`.venv/bin/python -m app.seed`

Tạo: 1 quản trị, 2 giáo viên, 3 lớp, 1 Unit nội dung mẫu của lớp 8 và 25 câu
kiểm tra đầu vào (ngữ pháp 10, đọc 8, nghe 7) theo đúng mục 3.9.
"""
import json
import random
import string

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from app.db import Base, SessionLocal, engine
from app.models import Class, Lesson, Question, Unit, User
from app.services.placement import PLACEMENT_LESSON_CODE, PLACEMENT_UNIT_CODE
from app.services.security import hash_password

SEED_PASSWORD = "matkhau123"

GRAMMAR = [
    ("My village ______ famous for its handicraft.", ["is", "are", "be", "been"], "A",
     "Chủ ngữ số ít 'My village' → dùng 'is'."),
    ("If it ______ tomorrow, we will stay at home.", ["rains", "will rain", "rained", "raining"], "A",
     "Mệnh đề if loại 1 dùng hiện tại đơn."),
    ("She has lived here ______ 2019.", ["since", "for", "in", "at"], "A",
     "'since' đi với mốc thời gian."),
    ("This is the museum ______ we visited last week.", ["which", "who", "whose", "where"], "A",
     "Đại từ quan hệ cho vật làm tân ngữ: which."),
    ("The streets are ______ than they were ten years ago.", ["cleaner", "cleanest", "clean", "more clean"], "A",
     "So sánh hơn với tính từ ngắn: cleaner."),
    ("We should ______ plastic bags to protect the environment.", ["reduce", "reducing", "reduced", "to reduce"], "A",
     "Sau 'should' là động từ nguyên thể."),
    ("A lot of trees ______ in our school last month.", ["were planted", "planted", "are planting", "plant"], "A",
     "Bị động quá khứ, chủ ngữ số nhiều."),
    ("Nam asked me ______ I had finished my homework.", ["if", "that", "what", "which"], "A",
     "Câu gián tiếp dạng yes/no dùng 'if'."),
    ("Would you mind ______ the window?", ["opening", "open", "to open", "opened"], "A",
     "'Would you mind + V-ing'."),
    ("This is ______ most beautiful temple in the region.", ["the", "a", "an", "Ø"], "A",
     "So sánh nhất cần mạo từ xác định 'the'."),
]

READING = [
    ("Đọc đoạn văn sau:\n“Duong Lam is an ancient village about 50 km from Hanoi. "
     "It is famous for its old houses made of laterite, its village gates and its traditional "
     "soy sauce. Visitors can walk or cycle around the village. Many families still live there "
     "and open their doors to tourists.”\n\nĐoạn văn chủ yếu nói về điều gì?",
     ["Một ngôi làng cổ nổi tiếng", "Một thành phố lớn", "Một khu chợ đêm", "Một bãi biển"], "A",
     "Câu đầu nêu chủ đề: làng cổ Duong Lam."),
    ("Theo đoạn văn, Duong Lam nổi tiếng vì:",
     ["nhà cổ bằng đá ong", "nhà cao tầng", "công viên nước", "sân bay"], "A",
     "'old houses made of laterite' = nhà cổ bằng đá ong."),
    ("Duong Lam cách Hà Nội khoảng bao xa?",
     ["50 km", "5 km", "500 km", "15 km"], "A", "Đoạn văn ghi 'about 50 km from Hanoi'."),
    ("Khách du lịch có thể làm gì ở làng?",
     ["Đi bộ hoặc đạp xe", "Chỉ ngồi trong xe", "Không được vào làng", "Chỉ mua vé"], "A",
     "'walk or cycle around the village'."),
    ("Từ 'laterite' trong đoạn gần nghĩa nhất với từ nào?",
     ["đá ong", "gỗ quý", "xi măng", "kính"], "A", "laterite là đá ong — vật liệu làm nhà cổ."),
    ("Ai còn sống trong làng?",
     ["Nhiều gia đình địa phương", "Chỉ khách du lịch", "Không ai", "Chỉ học sinh"], "A",
     "'Many families still live there'."),
    ("Đoạn văn nhắc đến sản phẩm truyền thống nào?",
     ["Nước tương", "Cà phê", "Trà sữa", "Bánh mì"], "A", "'traditional soy sauce' = nước tương."),
    ("Thái độ của tác giả với ngôi làng là:",
     ["Trân trọng, giới thiệu", "Chê bai", "Lo lắng", "Không quan tâm"], "A",
     "Tác giả mô tả tích cực và mời khách tham quan."),
]

LISTENING = [
    ("[Audio] Nghe đoạn hội thoại ngắn rồi chọn đáp án: hai bạn nói về việc gì?",
     ["Cuối tuần đi đâu", "Bài kiểm tra Toán", "Mua điện thoại", "Kế hoạch nghỉ hè"], "A",
     "Audio mẫu — nội dung thật do nhóm Nội dung (An) cung cấp ở Sprint 1."),
    ("[Audio] Người nói đề nghị gặp nhau lúc mấy giờ?",
     ["3 giờ", "8 giờ", "10 giờ", "12 giờ"], "A", "Audio mẫu."),
    ("[Audio] Họ sẽ di chuyển bằng phương tiện gì?",
     ["Xe đạp", "Máy bay", "Tàu hoả", "Thuyền"], "A", "Audio mẫu."),
    ("[Audio] Thời tiết cuối tuần được dự báo thế nào?",
     ["Có mưa", "Nắng nóng", "Có tuyết", "Có bão"], "A", "Audio mẫu."),
    ("[Audio] Ai sẽ mang đồ ăn?",
     ["Lan", "Nam", "Cô giáo", "Không ai"], "A", "Audio mẫu."),
    ("[Audio] Họ hẹn gặp ở đâu?",
     ["Cổng trường", "Siêu thị", "Bến xe", "Thư viện"], "A", "Audio mẫu."),
    ("[Audio] Người nói cảm thấy thế nào về kế hoạch?",
     ["Hào hứng", "Chán", "Lo lắng", "Tức giận"], "A", "Audio mẫu."),
]


def _join_code(n=6) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=n))


def ensure_users_and_classes(db: OrmSession) -> None:
    if db.execute(select(User).where(User.email == "admin@truong.edu.vn")).scalar_one_or_none():
        return
    admin = User(email="admin@truong.edu.vn", password_hash=hash_password(SEED_PASSWORD),
                 full_name="Quản trị hệ thống", role="admin")
    teacher = User(email="gv.an@truong.edu.vn", password_hash=hash_password(SEED_PASSWORD),
                   full_name="Nguyễn Thị An", role="teacher")
    db.add_all([admin, teacher])
    db.flush()
    db.add_all([
        Class(name="8A1 — Tiếng Anh", grade=8, join_code="8A1X21", teacher_id=teacher.id),
        Class(name="8A2 — Tiếng Anh", grade=8, join_code="8A2X22", teacher_id=teacher.id),
        Class(name="10A1 — Tiếng Anh", grade=10, join_code="10A1X2", teacher_id=teacher.id),
    ])
    db.commit()


def ensure_placement_content(db: OrmSession) -> None:
    """25 câu kiểm tra đầu vào: ngữ pháp 10, đọc 8, nghe 7 (mục 3.9)."""
    if db.execute(select(Lesson).where(Lesson.code == PLACEMENT_LESSON_CODE)).scalar_one_or_none():
        return
    unit = Unit(grade=0, code=PLACEMENT_UNIT_CODE, title="Bài kiểm tra đầu vào", order_no=0)
    db.add(unit)
    db.flush()
    lesson = Lesson(unit_id=unit.id, code=PLACEMENT_LESSON_CODE,
                    title="Placement 25 câu + bài viết", skill="mixed",
                    content=json.dumps({"note": "Ngân hàng câu hỏi dùng chung cho mọi lớp"}, ensure_ascii=False),
                    order_no=0)
    db.add(lesson)
    db.flush()

    order = 0
    for skill, bank in (("grammar", GRAMMAR), ("reading", READING), ("listening", LISTENING)):
        for i, (prompt, options, key, explain) in enumerate(bank):
            order += 1
            # Trong ngân hàng trên, đáp án đúng luôn ở vị trí đầu; xoay vị trí để đáp án
            # đúng nằm rải ở A/B/C/D — tránh học sinh đoán "toàn A".
            correct_text = options[0]
            rest = options[1:]
            pos = (order - 1) % 4
            rotated = rest[:pos] + [correct_text] + rest[pos:]
            db.add(Question(lesson_id=lesson.id, qtype="mcq", skill=skill, order_no=order,
                            prompt=prompt, options=json.dumps(rotated),
                            correct_key="ABCD"[pos], explanation=explain))
    db.commit()


def ensure_demo_unit(db: OrmSession) -> None:
    if db.execute(select(Unit).where(Unit.code == "U1", Unit.grade == 8)).scalar_one_or_none():
        return
    unit = Unit(grade=8, code="U1", title="Local Environment", order_no=1)
    db.add(unit)
    db.flush()
    lesson = Lesson(
        unit_id=unit.id, code="U1-L1", title="Getting Started — Our Local Environment",
        skill="vocab", order_no=1,
        content=json.dumps({
            "objectives": ["Nêu được 5 địa điểm trong khu vực sống",
                           "Dùng được thì hiện tại đơn miêu tả nơi chốn"],
            "vocab": [{"word": "market", "vi": "chợ"},
                      {"word": "temple", "vi": "đền, chùa"},
                      {"word": "handicraft", "vi": "đồ thủ công"}],
            "grammar": "Hiện tại đơn: S + V(s/es) — miêu tả đặc điểm nơi chốn.",
        }, ensure_ascii=False),
        transcript="Our village is famous for its handicraft. Every Sunday, people go to the market...",
    )
    db.add(lesson)
    db.flush()
    for i in range(1, 11):
        db.add(Question(lesson_id=lesson.id, qtype="mcq", skill="grammar", order_no=i,
                        prompt=f"Câu mẫu {i}: My village ______ famous for its handicraft.",
                        options=json.dumps(["is", "are", "be", "been"]), correct_key="A",
                        explanation="Chủ ngữ số ít 'My village' → dùng 'is'."))
    db.commit()


def main() -> None:
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        ensure_users_and_classes(db)
        ensure_demo_unit(db)
        ensure_placement_content(db)
        print("Dữ liệu mẫu sẵn sàng:")
        print(f"  Quản trị : admin@truong.edu.vn / {SEED_PASSWORD}")
        print(f"  Giáo viên: gv.an@truong.edu.vn / {SEED_PASSWORD}")
        print("  Mã lớp   : 8A1X21 · 8A2X22 · 10A1X2")
        print("  Placement: 25 câu (10 ngữ pháp, 8 đọc, 7 nghe)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
