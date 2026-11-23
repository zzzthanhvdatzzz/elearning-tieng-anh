"""Sinh file Excel mẫu để nhóm Nội dung điền câu hỏi (định dạng của trang Import).

`~/.venv-docx/bin/python scripts/make_question_template.py`
→ data/templates/mau_cau_hoi.xlsx  (sheet 1: dữ liệu, sheet 2: hướng dẫn)
"""
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
from openpyxl.utils import get_column_letter

HEADER = ["skill", "prompt", "option_a", "option_b", "option_c", "option_d",
          "correct_key", "explanation"]

SAMPLES = [
    ["grammar", "My village ______ famous for its handicraft.", "is", "are", "be", "been",
     "A", "Chủ ngữ số ít nên dùng 'is'."],
    ["grammar", "People here ______ pottery every day.", "make", "makes", "making", "made",
     "A", "Chủ ngữ số nhiều nên dùng động từ nguyên mẫu."],
    ["reading", "Theo đoạn văn, Duong Lam nổi tiếng vì gì?", "nhà cổ bằng đá ong", "nhà cao tầng",
     "công viên nước", "sân bay", "A", "Đoạn văn nhắc 'old houses made of laterite'."],
    ["listening", "[Audio] Hai bạn nói về việc gì?", "Kế hoạch cuối tuần", "Bài kiểm tra Toán",
     "Mua điện thoại", "Nghỉ hè", "A", "Audio 1, đoạn 1."],
    ["vocab", "Từ “artisan” có nghĩa là gì?", "nghệ nhân", "khách du lịch", "học sinh", "nông dân",
     "A", "artisan = nghệ nhân."],
]

GUIDE = [
    ("Cột", "Bắt buộc", "Giá trị hợp lệ / ghi chú"),
    ("skill", "Có", "grammar | reading | listening | vocab | writing | speaking"),
    ("prompt", "Có", "Nội dung câu hỏi. Với bài nghe, bắt đầu bằng [Audio] và ghi rõ số hiệu audio."),
    ("option_a … option_d", "Có", "Đúng bốn lựa chọn, không để trống ô nào."),
    ("correct_key", "Có", "A | B | C | D — trùng với vị trí đáp án đúng."),
    ("explanation", "Không", "Giải thích hiện cho học sinh sau khi nộp bài."),
    ("", "", ""),
    ("Quy tắc", "", "Dòng sai bị bỏ qua và liệt kê lý do; dòng đúng vẫn được nhập (AC15.2)."),
    ("Quy tắc", "", "Không sửa tên sheet, không thêm dòng tiêu đề phụ ở trên."),
    ("Quy tắc", "", "Mỗi bài 10 câu; 4 Unit × 6 bài = 240 câu."),
]


def main() -> None:
    out = Path("data/templates")
    out.mkdir(parents=True, exist_ok=True)

    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "cau_hoi"
    ws.append(HEADER)
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(vertical="center")
    for row in SAMPLES:
        ws.append(row)

    widths = [12, 52, 18, 18, 18, 18, 12, 40]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A2"

    gs = wb.create_sheet("huong_dan")
    for row in GUIDE:
        gs.append(list(row))
    gs.column_dimensions["A"].width = 20
    gs.column_dimensions["B"].width = 12
    gs.column_dimensions["C"].width = 90

    path = out / "mau_cau_hoi.xlsx"
    wb.save(path)
    print(f"{path} — {path.stat().st_size} bytes")


if __name__ == "__main__":
    main()
