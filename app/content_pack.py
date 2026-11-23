"""content_pack.py — 4 Unit × 6 bài × 10 câu (240 câu) theo khung sách giáo khoa.

LƯU Ý TRUNG THỰC: câu hỏi ở đây sinh tự động từ bộ từ vựng của từng bài
(5 câu Anh→Việt và 5 câu Việt→Anh, phương án nhiễu lấy từ chính Unit đó).
Đây là **ngân hàng từ vựng**, không thay thế được đề ngữ pháp/đọc/nghe do An soạn.
Nhóm Nội dung cần rà lại nghĩa tiếng Việt và bổ sung câu ngữ pháp trước khi dùng thật.
"""
from __future__ import annotations

import json
import random

from sqlalchemy import func, select
from sqlalchemy.orm import Session as OrmSession

from app.models import Lesson, Question, Unit

# (mã Unit, khối, tiêu đề) → 6 bài, mỗi bài: mã bài, tiêu đề, kỹ năng, số phút, mục tiêu, từ vựng
PACK = [
    # ---------------------------------------------------------------- LỚP 8 — UNIT 1
    {
        "unit": ("U1", 8, "Local Environment"),
        "lessons": [
            ("U1-L1", "Getting Started — Our Local Environment", "vocab", 10,
             ["Nêu được địa điểm trong khu vực sống"],
             [("market", "chợ"), ("temple", "đền, chùa"), ("handicraft", "đồ thủ công"),
              ("pottery", "đồ gốm")]),
            ("U1-L2", "A Closer Look 1 — Vocabulary", "vocab", 12,
             ["Mở rộng 8 từ về nghề truyền thống"],
             [("artisan", "nghệ nhân"), ("workshop", "xưởng"), ("carve", "chạm khắc"),
              ("weave", "dệt")]),
            ("U1-L3", "A Closer Look 2 — Grammar", "grammar", 12,
             ["Phân biệt hiện tại đơn và hiện tại tiếp diễn"],
             [("village", "làng"), ("neighbourhood", "khu dân cư"), ("crowded", "đông đúc"),
              ("peaceful", "yên bình")]),
            ("U1-L4", "Communication — Asking the Way", "speaking", 10,
             ["Hỏi và chỉ đường trong khu vực sống"],
             [("turn left", "rẽ trái"), ("go straight", "đi thẳng"), ("opposite", "đối diện"),
              ("corner", "góc phố")]),
            ("U1-L5", "Skills 1 — Reading", "reading", 15,
             ["Đọc hiểu đoạn văn 150 từ về làng nghề"],
             [("ancient", "cổ xưa"), ("laterite", "đá ong"), ("soy sauce", "nước tương"),
              ("visitor", "khách tham quan")]),
            ("U1-L6", "Skills 2 — Writing", "writing", 15,
             ["Viết đoạn 80 từ giới thiệu nơi mình sống"],
             [("friendly", "thân thiện"), ("fresh air", "không khí trong lành"),
              ("convenient", "thuận tiện"), ("noisy", "ồn ào")]),
        ],
    },
    # ---------------------------------------------------------------- LỚP 8 — UNIT 2
    {
        "unit": ("U2", 8, "Shopping"),
        "lessons": [
            ("U2-L1", "Getting Started — Let's Go Shopping", "vocab", 10,
             ["Nói về hoạt động mua sắm hằng ngày"],
             [("shopping mall", "trung tâm mua sắm"), ("grocery", "cửa hàng thực phẩm"),
              ("discount", "giảm giá"), ("receipt", "hoá đơn")]),
            ("U2-L2", "A Closer Look 1 — Vocabulary", "vocab", 12,
             ["Mở rộng từ về hàng hoá và giá cả"],
             [("bargain", "món hời"), ("expensive", "đắt"), ("cheap", "rẻ"),
              ("quality", "chất lượng")]),
            ("U2-L3", "A Closer Look 2 — Grammar", "grammar", 12,
             ["Dùng 'too' và 'enough'"],
             [("customer", "khách hàng"), ("shop assistant", "nhân viên bán hàng"),
              ("size", "kích cỡ"), ("refund", "hoàn tiền")]),
            ("U2-L4", "Communication — Buying Things", "speaking", 10,
             ["Hỏi giá và mặc cả lịch sự"],
             [("How much is it?", "Cái này giá bao nhiêu?"),
              ("Can I try it on?", "Tôi thử được không?"),
              ("in stock", "còn hàng"), ("sold out", "hết hàng")]),
            ("U2-L5", "Skills 1 — Reading", "reading", 15,
             ["Đọc hiểu về mua sắm trực tuyến"],
             [("online shopping", "mua sắm trực tuyến"), ("delivery", "giao hàng"),
              ("review", "đánh giá"), ("convenient", "tiện lợi")]),
            ("U2-L6", "Skills 2 — Writing", "writing", 15,
             ["Viết đoạn nêu ý kiến về mua sắm trực tuyến"],
             [("compare", "so sánh"), ("advantage", "lợi thế"), ("disadvantage", "bất lợi"),
              ("budget", "ngân sách")]),
        ],
    },
    # ---------------------------------------------------------------- LỚP 10 — UNIT 1
    {
        "unit": ("10-U1", 10, "Family Life"),
        "lessons": [
            ("10-U1-L1", "Getting Started — Family Life", "vocab", 10,
             ["Nói về công việc nhà trong gia đình"],
             [("household chores", "việc nhà"), ("share", "chia sẻ"), ("responsibility", "trách nhiệm"),
              ("generation", "thế hệ")]),
            ("10-U1-L2", "A Closer Look 1 — Vocabulary", "vocab", 12,
             ["Mở rộng từ về vai trò trong gia đình"],
             [("breadwinner", "người trụ cột"), ("homemaker", "người nội trợ"),
              ("support", "ủng hộ"), ("respect", "tôn trọng")]),
            ("10-U1-L3", "A Closer Look 2 — Grammar", "grammar", 12,
             ["Dùng hiện tại hoàn thành và quá khứ đơn"],
             [("raise", "nuôi dạy"), ("obey", "vâng lời"), ("argue", "tranh cãi"),
              ("solve", "giải quyết")]),
            ("10-U1-L4", "Communication — Family Rules", "speaking", 10,
             ["Thảo luận về nội quy gia đình"],
             [("allow", "cho phép"), ("forbid", "cấm"), ("permission", "sự cho phép"),
              ("curfew", "giờ giới nghiêm")]),
            ("10-U1-L5", "Skills 1 — Reading", "reading", 15,
             ["Đọc hiểu về gia đình nhiều thế hệ"],
             [("extended family", "gia đình nhiều thế hệ"), ("nuclear family", "gia đình hạt nhân"),
              ("bond", "gắn kết"), ("tradition", "truyền thống")]),
            ("10-U1-L6", "Skills 2 — Writing", "writing", 15,
             ["Viết đoạn về vai trò của người cha/mẹ"],
             [("role model", "hình mẫu"), ("encourage", "khuyến khích"), ("patient", "kiên nhẫn"),
              ("strict", "nghiêm khắc")]),
        ],
    },
    # ---------------------------------------------------------------- LỚP 10 — UNIT 2
    {
        "unit": ("10-U2", 10, "Humans and the Environment"),
        "lessons": [
            ("10-U2-L1", "Getting Started — Our Environment", "vocab", 10,
             ["Nói về vấn đề môi trường quanh em"],
             [("pollution", "ô nhiễm"), ("plastic waste", "rác thải nhựa"),
              ("recycle", "tái chế"), ("litter", "rác vụn")]),
            ("10-U2-L2", "A Closer Look 1 — Vocabulary", "vocab", 12,
             ["Mở rộng từ về bảo vệ môi trường"],
             [("deforestation", "phá rừng"), ("emission", "khí thải"),
              ("renewable", "tái tạo được"), ("fossil fuel", "nhiên liệu hoá thạch")]),
            ("10-U2-L3", "A Closer Look 2 — Grammar", "grammar", 12,
             ["Dùng câu bị động và mệnh đề quan hệ"],
             [("endanger", "gây nguy hiểm"), ("protect", "bảo vệ"), ("damage", "làm hư hại"),
              ("preserve", "gìn giữ")]),
            ("10-U2-L4", "Communication — Green Habits", "speaking", 10,
             ["Thuyết phục người khác thay đổi thói quen"],
             [("persuade", "thuyết phục"), ("habit", "thói quen"), ("instead of", "thay vì"),
              ("reduce", "giảm")]),
            ("10-U2-L5", "Skills 1 — Reading", "reading", 15,
             ["Đọc hiểu về biến đổi khí hậu"],
             [("climate change", "biến đổi khí hậu"), ("global warming", "nóng lên toàn cầu"),
              ("sea level", "mực nước biển"), ("drought", "hạn hán")]),
            ("10-U2-L6", "Skills 2 — Writing", "writing", 15,
             ["Viết đoạn đề xuất giải pháp môi trường"],
             [("solution", "giải pháp"), ("awareness", "nhận thức"), ("volunteer", "tình nguyện"),
              ("campaign", "chiến dịch")]),
        ],
    },
]

READING_SNIPPET = {
    "reading": ("Many villages in Viet Nam still keep their traditional crafts. Local people "
                "make pottery, weave cloth and carve wood. Visitors can watch the artisans work "
                "and buy their products directly."),
    "writing": "Cấu trúc: câu chủ đề → 2–3 chi tiết → câu kết.",
    "grammar": "Ôn tập cấu trúc trọng tâm của bài; xem ghi chú trong sách giáo khoa.",
    "speaking": "Luyện nói 45–60 giây, dùng đủ các từ vựng của bài.",
    "vocab": "Học 4 từ mới và đặt câu với mỗi từ.",
}


GRAMMAR_FRAMES = {
    "U1": [
        ("My village ______ famous for its handicraft.", ["is", "are", "be", "been"], "A",
         "Chủ ngữ số ít → is."),
        ("People here ______ pottery every day.", ["make", "makes", "making", "made"], "A",
         "Chủ ngữ số nhiều → động từ nguyên mẫu."),
        ("There ______ a temple opposite my house.", ["is", "are", "have", "has"], "A",
         "'There is' với danh từ số ít."),
        ("She ______ to the market every Sunday.", ["goes", "go", "going", "gone"], "A",
         "Ngôi thứ ba số ít → goes."),
    ],
    "U2": [
        ("This shirt is ______ expensive for me.", ["too", "enough", "very much", "so that"], "A",
         "'too + adj' = quá … không thể."),
        ("The bag isn't cheap ______ for students.", ["enough", "too", "so", "such"], "A",
         "'adj + enough' = đủ …"),
        ("How ______ does this T-shirt cost?", ["much", "many", "long", "far"], "A",
         "Hỏi giá dùng 'how much'."),
        ("I'd like ______ this jacket, please.", ["to try", "trying", "try", "tried"], "A",
         "'would like + to V'."),
    ],
    "10-U1": [
        ("My mother ______ the household chores since morning.", ["has done", "did", "does", "doing"],
         "A", "Hiện tại hoàn thành với 'since'."),
        ("We ______ this rule last year.", ["discussed", "have discussed", "discuss", "discussing"], "A",
         "Mốc thời gian quá khứ → quá khứ đơn."),
        ("Children should ______ their parents.", ["respect", "respecting", "respected", "to respect"], "A",
         "Sau 'should' là động từ nguyên thể."),
        ("My father is the ______ of the family.", ["breadwinner", "breadwin", "winning", "winner bread"],
         "A", "Cụm cố định 'breadwinner'."),
    ],
    "10-U2": [
        ("Plastic waste ______ into the sea every year.", ["is dumped", "dumps", "dumping", "dump"], "A",
         "Bị động hiện tại đơn."),
        ("We should ______ energy at home.", ["save", "saving", "saved", "to save"], "A",
         "Sau 'should' là động từ nguyên thể."),
        ("The forest ______ we visited is being destroyed.", ["which", "who", "whose", "where"], "A",
         "Đại từ quan hệ cho vật."),
        ("If we recycle more, we ______ less waste.", ["will produce", "produced", "producing", "would produce"],
         "A", "Câu điều kiện loại 1."),
    ],
}


def _questions_for(vocab, unit_pool, rng: random.Random, unit_code: str) -> list[dict]:
    """10 câu/bài: 4 Anh→Việt + 4 Việt→Anh + 2 ngữ pháp theo Unit."""
    out: list[dict] = []
    letters = "ABCD"

    for word, vi in vocab[:4]:
        distractors = [v for (w, v) in unit_pool if v != vi]
        rng.shuffle(distractors)
        opts = [vi] + distractors[:3]
        rng.shuffle(opts)
        out.append({
            "skill": "vocab",
            "prompt": f"Từ “{word}” có nghĩa là gì?",
            "options": opts,
            "correct_key": letters[opts.index(vi)],
            "explanation": f"{word} = {vi}",
        })

    for word, vi in vocab[:4]:
        others = [w for (w, _) in unit_pool if w != word]
        rng.shuffle(others)
        opts = [word] + others[:3]
        rng.shuffle(opts)
        out.append({
            "skill": "vocab",
            "prompt": f"Từ tiếng Anh nào có nghĩa là “{vi}”?",
            "options": opts,
            "correct_key": letters[opts.index(word)],
            "explanation": f"{vi} = {word}",
        })

    frames = GRAMMAR_FRAMES.get(unit_code, [])
    for prompt, options, key, explain in frames[:2]:
        opts = list(options)
        rng.shuffle(opts)
        out.append({
            "skill": "grammar",
            "prompt": prompt,
            "options": opts,
            "correct_key": letters[opts.index(options[0])],
            "explanation": explain,
        })

    return out


def ensure_content(db: OrmSession) -> dict:
    """Nạp 4 Unit, 24 bài, 240 câu. Idempotent: bài/câu đã có thì bỏ qua."""
    rng = random.Random(2026)
    units = lessons_created = questions_created = 0

    for block in PACK:
        code, grade, title = block["unit"]
        unit = db.execute(
            select(Unit).where(Unit.code == code, Unit.grade == grade)
        ).scalar_one_or_none()
        if unit is None:
            unit = Unit(grade=grade, code=code, title=title,
                        order_no=1 if code.endswith("U1") or code == "U1" else 2)
            db.add(unit)
            db.flush()
            units += 1

        unit_pool = [pair for lesson in block["lessons"] for pair in lesson[5]]

        for order, (lcode, ltitle, skill, minutes, objectives, vocab) in enumerate(
                block["lessons"], start=1):
            lesson = db.execute(select(Lesson).where(Lesson.code == lcode)).scalar_one_or_none()
            if lesson is None:
                lesson = Lesson(
                    unit_id=unit.id, code=lcode, title=ltitle, skill=skill, order_no=order,
                    content=json.dumps({
                        "objectives": objectives,
                        "vocab": [{"word": w, "vi": v} for w, v in vocab],
                        "grammar": READING_SNIPPET.get(skill, ""),
                        "reading": READING_SNIPPET["reading"] if skill == "reading" else None,
                        "minutes": minutes,
                    }, ensure_ascii=False),
                    transcript=READING_SNIPPET["reading"] if skill == "listening" else None,
                )
                db.add(lesson)
                db.flush()
                lessons_created += 1
            else:
                # bài đã có từ seed cũ: chỉ bổ sung từ vựng nếu đang trống
                try:
                    content = json.loads(lesson.content or "{}")
                except json.JSONDecodeError:
                    content = {}
                if not content.get("vocab"):
                    content["vocab"] = [{"word": w, "vi": v} for w, v in vocab]
                    content.setdefault("objectives", objectives)
                    content.setdefault("minutes", minutes)
                    lesson.content = json.dumps(content, ensure_ascii=False)
                    db.commit()

            existing = db.execute(
                select(func.count()).select_from(Question).where(Question.lesson_id == lesson.id)
            ).scalar_one()
            if existing >= 10:
                continue                       # bài đã đủ 10 câu

            start_order = db.execute(
                select(func.coalesce(func.max(Question.order_no), 0))
                .where(Question.lesson_id == lesson.id)
            ).scalar_one()
            generated = _questions_for(vocab, unit_pool, rng, code)
            # bù cho đủ 10 câu nếu bài đã có sẵn vài câu
            for i, q in enumerate(generated[existing:], start=start_order + 1):
                db.add(Question(
                    lesson_id=lesson.id, qtype="mcq", skill=q["skill"], order_no=i,
                    prompt=q["prompt"], options=json.dumps(q["options"], ensure_ascii=False),
                    correct_key=q["correct_key"], explanation=q["explanation"],
                ))
                questions_created += 1
        db.commit()

    return {"units": units, "lessons": lessons_created, "questions": questions_created}


if __name__ == "__main__":
    from app.db import Base, SessionLocal, engine

    Base.metadata.create_all(engine)
    s = SessionLocal()
    try:
        print(ensure_content(s))
    finally:
        s.close()
