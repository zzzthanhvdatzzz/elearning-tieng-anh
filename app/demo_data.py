"""demo_data.py — tạo một kịch bản demo ĐẦY ĐỦ để mở lên là thấy dữ liệu thật.

    .venv/bin/python -m app.demo_data

Tạo (idempotent, chạy lại không nhân đôi):
- 3 lớp của giáo viên (đã có từ seed) + 12 học sinh rải ở 8A1 và 10A1
- mỗi học sinh: 1 bài kiểm tra đầu vào đã chấm (có CEFR), tiến độ học, 1-2 lượt luyện tập
- 2 bài viết đang chờ giáo viên chấm, 1 bài đã chấm có nhận xét
- 1 phụ huynh đã được duyệt liên kết với 1 học sinh
- 1 bài giao có deadline cho lớp 8A1

Mật khẩu mọi tài khoản demo: matkhau123
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta

from sqlalchemy import select

from app.content_pack import ensure_content
from app.db import Base, SessionLocal, engine
from app.models import (
    Answer, Assignment, AssignmentQuestion, Class, Enrollment, Lesson, ParentLink,
    Progress, Question, RubricScore, Submission, Unit, User,
)
from app.seed import ensure_demo_unit, ensure_placement_content, ensure_users_and_classes
from app.services.security import hash_password

PASSWORD = "matkhau123"
STUDENTS_8 = [
    ("Nguyễn Minh Anh", "an.nm@truong.edu.vn"),
    ("Trần Đức Huy", "huy.td@truong.edu.vn"),
    ("Lê Thu Trang", "trang.lt@truong.edu.vn"),
    ("Phạm Quốc Bảo", "bao.pq@truong.edu.vn"),
    ("Hoàng Khánh Linh", "linh.hk@truong.edu.vn"),
    ("Vũ Nhật Nam", "nam.vn@truong.edu.vn"),
    ("Đỗ Thị Mai", "mai.dt@truong.edu.vn"),
    ("Bùi Gia Hân", "han.bg@truong.edu.vn"),
]
STUDENTS_10 = [
    ("Ngô Thanh Tùng", "tung.nt@truong.edu.vn"),
    ("Dương Thu Hà", "ha.dt@truong.edu.vn"),
    ("Trịnh Văn Long", "long.tv@truong.edu.vn"),
    ("Nguyễn Bảo Châu", "chau.nb@truong.edu.vn"),
]

ESSAYS = [
    ("I live in a small neighbourhood near the sea. There is a market, a temple and a long "
     "beach. Every morning I ride my bike around the town with my friends. I love my town "
     "because people are friendly and the air is clean."),
    ("My village is famous for pottery. My grandfather is an artisan and he works in a small "
     "workshop near the river. Visitors come to buy bowls and vases. I am proud of my village "
     "and I want to keep this tradition alive."),
    ("Shopping online is convenient because we can compare prices and buy things at home. "
     "However, we cannot try clothes before buying, and delivery can be slow. I think it is "
     "good for books and electronics, but not for shoes."),
]


def _user(db, email, name, role="student") -> User:
    u = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if u is None:
        u = User(email=email, password_hash=hash_password(PASSWORD), full_name=name, role=role)
        db.add(u)
        db.flush()
    return u


def _enroll(db, klass: Class, student: User) -> None:
    row = db.execute(select(Enrollment).where(
        Enrollment.class_id == klass.id, Enrollment.student_id == student.id)).scalar_one_or_none()
    if row is None:
        db.add(Enrollment(class_id=klass.id, student_id=student.id))
        db.commit()


def _graded_placement(db, student: User, klass: Class, teacher: User, rng: random.Random) -> None:
    """Nộp và chấm bài placement để học sinh có CEFR + báo cáo có số liệu."""
    from app.services.placement import ensure_placement_assignment, grade_placement, placement_questions

    assignment = ensure_placement_assignment(db, klass)
    if assignment is None:
        return
    exists = db.execute(select(Submission).where(
        Submission.assignment_id == assignment.id, Submission.student_id == student.id)).scalar_one_or_none()
    if exists is not None:
        return

    questions = placement_questions(db)
    answers, detail = {}, []
    correct = 0
    for q in questions:
        right = rng.random() < 0.65          # ~65% đúng cho dữ liệu trông tự nhiên
        choice = q.correct_key if right else next(
            (k for k in "ABCD" if k != q.correct_key), "A")
        answers[q.id] = choice
        correct += int(right)
        detail.append({"question_id": q.id, "choice": choice, "is_correct": right})

    from app.services.scoring import auto_score

    mcq = auto_score(correct, len(questions))
    sub = Submission(assignment_id=assignment.id, student_id=student.id, attempt_no=1,
                     status="awaiting_teacher", auto_score=mcq, text_content=" ".join(["word"] * 70))
    db.add(sub)
    db.flush()
    for d in detail:
        db.add(Answer(submission_id=sub.id, question_id=d["question_id"],
                      choice=d["choice"], is_correct=d["is_correct"]))
    db.commit()

    writing = round(rng.uniform(4.0, 9.5) * 2) / 2
    rubric = {"task": min(2.5, writing / 4), "grammar": min(2.5, writing / 4),
              "vocab": min(2.5, writing / 4), "coherence": min(2.5, writing / 4)}
    grade_placement(db, sub, rubric, teacher, 0,
                    "Nhận xét tự động của dữ liệu demo." if writing < 5 else "")


def _practice(db, student: User, lesson: Lesson, rng: random.Random, attempts: int = 2) -> None:
    from app.services.practice import ensure_practice_assignment, lesson_questions
    from app.services.placement import active_class
    from app.services.scoring import auto_score

    klass = active_class(db, student.id)
    if klass is None:
        return
    qs = lesson_questions(db, lesson.id)
    if not qs:
        return
    assignment = ensure_practice_assignment(db, klass, lesson, qs)
    used = db.execute(select(Submission).where(
        Submission.assignment_id == assignment.id, Submission.student_id == student.id)).scalars().all()

    for n in range(len(used) + 1, attempts + 1):
        correct, answers = 0, []
        for q in qs:
            right = rng.random() < 0.7
            choice = q.correct_key if right else next((k for k in "ABCD" if k != q.correct_key), "A")
            correct += int(right)
            answers.append((q.id, choice, right))
        score = auto_score(correct, len(qs))
        sub = Submission(assignment_id=assignment.id, student_id=student.id, attempt_no=n,
                         status="graded", auto_score=score, final_score=score,
                         graded_at=datetime.utcnow())
        db.add(sub)
        db.flush()
        for qid, choice, right in answers:
            db.add(Answer(submission_id=sub.id, question_id=qid, choice=choice, is_correct=right))
        db.commit()


def _progress(db, student: User, lesson: Lesson, percent: int, minutes: int) -> None:
    row = db.execute(select(Progress).where(
        Progress.student_id == student.id, Progress.lesson_id == lesson.id)).scalar_one_or_none()
    if row is None:
        db.add(Progress(student_id=student.id, lesson_id=lesson.id, percent=percent,
                        seconds=minutes * 60, last_seen_at=datetime.utcnow()))
        db.commit()


def main() -> None:
    Base.metadata.create_all(engine)
    rng = random.Random(2026)
    db = SessionLocal()
    try:
        ensure_users_and_classes(db)
        ensure_demo_unit(db)
        ensure_placement_content(db)
        ensure_content(db)

        teacher = db.execute(select(User).where(User.role == "teacher")).scalars().first()
        if teacher is None:
            print("Chưa có giáo viên — chạy `python -m app.seed` trước.")
            return

        classes = {c.join_code: c for c in db.execute(select(Class)).scalars().all()}
        k8 = classes.get("8A1X21") or list(classes.values())[0]
        k10 = classes.get("10A1X2") or k8

        created = 0
        for name, email in STUDENTS_8 + STUDENTS_10:
            s = _user(db, email, name)
            _enroll(db, k10 if email in [e for _, e in STUDENTS_10] else k8, s)
            created += 1

            _graded_placement(db, s, k10 if email in [e for _, e in STUDENTS_10] else k8, teacher, rng)

            grade = 10 if email in [e for _, e in STUDENTS_10] else 8
            lessons = db.execute(
                select(Lesson).join(Unit, Unit.id == Lesson.unit_id)
                .where(Unit.grade == grade)
                .order_by(Lesson.id)
            ).scalars().all()
            if not lessons:
                continue

            for i, lesson in enumerate(lessons[:3]):
                _progress(db, s, lesson, 100 if i == 0 else rng.choice([0, 25, 60]), rng.randint(4, 25))
            _practice(db, s, lessons[0], rng, attempts=rng.choice([1, 2, 3]))

        # 2 bài viết đang chờ + 1 bài đã chấm, để hàng đợi chấm có việc
        from app.services.writing import ensure_writing_assignment
        from app.services.grading import grade_writing

        writing_lesson = db.execute(select(Lesson).where(Lesson.code == "U1-L6")).scalar_one_or_none()
        if writing_lesson is not None:
            assignment = ensure_writing_assignment(db, k8, writing_lesson)
            for i, (name, email) in enumerate(STUDENTS_8[:3]):
                s = _user(db, email, name)
                sub = Submission(assignment_id=assignment.id, student_id=s.id, attempt_no=1,
                                 status="awaiting_teacher", text_content=ESSAYS[i],
                                 auto_score=None)
                db.add(sub)
                db.commit()
                if i == 0:
                    grade_writing(db, sub, {"task": 2.5, "grammar": 2.0, "vocab": 2.0, "coherence": 2.0},
                                  teacher, "Diễn đạt rõ, thêm ví dụ sẽ tốt hơn.")

        # phụ huynh đã duyệt với học sinh đầu tiên
        parent = _user(db, "phuhuynh.demo@truong.edu.vn", "Phụ huynh của Minh Anh", role="parent")
        student0 = _user(db, STUDENTS_8[0][1], STUDENTS_8[0][0])
        link = db.execute(select(ParentLink).where(
            ParentLink.parent_id == parent.id, ParentLink.student_id == student0.id)).scalar_one_or_none()
        if link is None:
            db.add(ParentLink(parent_id=parent.id, student_id=student0.id,
                              status="approved", approved_by=teacher.id))
            db.commit()

        # một bài giao có deadline cho lớp 8A1
        exists = db.execute(select(Assignment).where(
            Assignment.class_id == k8.id, Assignment.title == "Luyện tập Unit 1 — L1 (demo)"
        )).scalar_one_or_none()
        if exists is None:
            a = Assignment(class_id=k8.id, teacher_id=teacher.id, kind="practice",
                           lesson_id=db.execute(select(Lesson).where(Lesson.code == "U1-L1")).scalar_one().id,
                           title="Luyện tập Unit 1 — L1 (demo)",
                           deadline=datetime.utcnow() + timedelta(days=3),
                           max_attempts=3, weight_auto=1.0, weight_teacher=0.0)
            db.add(a)
            db.flush()
            qs = db.execute(select(Question).where(Question.lesson_id == a.lesson_id)
                            .order_by(Question.order_no)).scalars().all()
            for i, q in enumerate(qs, start=1):
                db.add(AssignmentQuestion(assignment_id=a.id, question_id=q.id, order_no=i))
            db.commit()

        print(f"Đã chuẩn bị dữ liệu demo cho {created} học sinh.")
        print("  Giáo viên : gv.an@truong.edu.vn / matkhau123")
        print("  Học sinh  : an.nm@truong.edu.vn / matkhau123 (lớp 8A1)")
        print("  Phụ huynh : phuhuynh.demo@truong.edu.vn / matkhau123")
        print("  Quản trị  : admin@truong.edu.vn / matkhau123")
    finally:
        db.close()


if __name__ == "__main__":
    main()
