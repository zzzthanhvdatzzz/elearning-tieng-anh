"""Gom toàn bộ model — import app.models là đủ để create_all/migration thấy 18 bảng."""
from app.models.content import Lesson, Question, Unit
from app.models.school import Class, Enrollment, ParentLink
from app.models.tracking import AuditLog, Badge, Notification, Progress, StudentBadge
from app.models.user import Session, User
from app.models.work import Answer, Assignment, AssignmentQuestion, RubricScore, Submission

__all__ = [
    "User", "Session",
    "Class", "Enrollment", "ParentLink",
    "Unit", "Lesson", "Question",
    "Assignment", "AssignmentQuestion", "Submission", "Answer", "RubricScore",
    "Progress", "Badge", "StudentBadge", "Notification", "AuditLog",
]
