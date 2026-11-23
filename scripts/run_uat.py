"""run_uat.py — chạy thật các kịch bản UAT kiểm được qua HTTP, ghi kết quả ra file.

    .venv/bin/python scripts/run_uat.py

Mỗi kịch bản in PASS/FAIL kèm bằng chứng (mã HTTP, giá trị đo). Kết quả được ghi vào
docs/UAT_RESULT.md để nhóm Kiểm thử dán vào biên bản.

KHÔNG kiểm được bằng script (phải làm tay, script sẽ ghi rõ ở cuối file):
ghi âm bằng micro trên điện thoại, p95 với 200 người, khôi phục sau sự cố, UAT người thật.
"""
from __future__ import annotations

import http.cookiejar
import io
import json
import statistics
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

API = "http://localhost:8010"
OUT = Path(__file__).resolve().parent.parent / "docs" / "UAT_RESULT.md"
PASSWORD = "matkhau123"

results: list[tuple[str, str, str, str]] = []   # (mã, mô tả, KQ, bằng chứng)


def record(code: str, desc: str, ok: bool, evidence: str) -> None:
    results.append((code, desc, "PASS" if ok else "FAIL", evidence))
    print(f"[{'PASS' if ok else 'FAIL'}] {code} — {desc} :: {evidence}")


class Client:
    def __init__(self) -> None:
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar),
            type("NoRedir", (urllib.request.HTTPRedirectHandler,),
                 {"redirect_request": lambda self, *a, **k: None}),
        )

    def request(self, path: str, data=None, method=None, headers=None, raw: bytes | None = None,
                content_type: str | None = None):
        h = {"X-Requested-With": "fetch"}
        if content_type:
            h["Content-Type"] = content_type
        elif data is not None:
            h["Content-Type"] = "application/json"
        if headers:
            h.update(headers)
        body = raw if raw is not None else (json.dumps(data).encode() if data is not None else None)
        req = urllib.request.Request(f"{API}{path}", data=body, headers=h,
                                     method=method or ("POST" if body else "GET"))
        try:
            r = self.opener.open(req, timeout=20)
            return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    def json(self, path, **kw):
        st, body = self.request(path, **kw)
        try:
            return st, json.loads(body)
        except json.JSONDecodeError:
            return st, {"raw": body[:200].decode(errors="replace")}

    def login(self, email: str) -> int:
        return self.request("/api/auth/login", {"email": email, "password": PASSWORD})[0]


def main() -> None:
    stamp = datetime.now().strftime("%d/%m/%Y %H:%M")

    # ---------------------------------------------------------------- 0. hạ tầng
    st, _ = Client().request("/health")
    record("NF-00", "API sống", st == 200, f"GET /health → {st}")

    c = Client()
    st, body = c.request("/api/units")
    record("SEC-01", "API không cho truy cập khi chưa đăng nhập", st == 401, f"{st}")

    st, _ = c.request("/api/auth/login", {"email": "x@y.z", "password": "x"},
                      headers={"X-Requested-With": ""})
    record("SEC-02", "Thiếu header CSRF bị chặn", st == 403, f"{st}")

    # ---------------------------------------------------------------- 1. học sinh
    fresh = f"uat.student.{int(time.time())}@truong.edu.vn"
    st, body = c.request("/api/auth/register", {"email": fresh, "password": PASSWORD,
                                               "full_name": "HS UAT", "join_code": "SAIMAA"})
    record("ST-02", "Đăng ký bằng mã lớp sai bị từ chối", st == 422, f"{st} {body[:60].decode(errors='replace')}")

    st, body = c.json("/api/auth/register", data={"email": fresh, "password": PASSWORD,
                                                 "full_name": "HS UAT", "join_code": "8A1X21"})
    record("ST-01", "Đăng ký bằng mã lớp đúng", st == 200 and body.get("role") == "student",
           f"{st} role={body.get('role')}")

    st, units = c.json("/api/units")
    n_lessons = sum(len(u["lessons"]) for u in units.get("units", []))
    record("ST-05", "Lộ trình hiện đúng khối lớp", st == 200 and n_lessons >= 6,
           f"{st} units={len(units.get('units', []))} lessons={n_lessons}")

    lesson_id = units["units"][0]["lessons"][0]["id"]
    st, detail = c.json(f"/api/lessons/{lesson_id}")
    record("ST-06a", "Mở bài học có nội dung", st == 200 and bool(detail.get("content")),
           f"{st} có từ vựng={bool(detail.get('content', {}).get('vocab'))}")

    st, prog = c.json(f"/api/lessons/{lesson_id}/progress", data={"seconds": 30})
    st2, prog2 = c.json(f"/api/lessons/{lesson_id}/progress", data={"seconds": 20})
    record("ST-06b", "Thời gian học cộng dồn, không mất",
           st == 200 and st2 == 200 and prog2["seconds"] == prog["seconds"] + 20,
           f"{prog.get('seconds')}s → {prog2.get('seconds')}s")

    st, exam = c.json(f"/api/practice/{lesson_id}")
    record("ST-07a", "Đề luyện tập không lộ đáp án",
           st == 200 and "correct_key" not in json.dumps(exam), f"{st} {len(exam.get('questions', []))} câu")

    answers = {str(q["id"]): "A" for q in exam["questions"]}
    t0 = time.perf_counter()
    st, res = c.json(f"/api/practice/{lesson_id}/submit", data={"answers": answers})
    elapsed = (time.perf_counter() - t0) * 1000
    record("ST-07b", "Chấm và trả điểm ngay (< 2 giây)",
           st == 200 and elapsed < 2000 and res.get("score") is not None,
           f"{st} điểm={res.get('score')} {elapsed:.0f} ms")

    codes = []
    for _ in range(4):
        codes.append(c.request(f"/api/practice/{lesson_id}/submit", {"answers": answers})[0])
    record("ST-08", "Hết lượt (3 lượt) thì chặn ở server", 409 in codes, f"các lần nộp: {codes}")

    # ---------------------------------------------------------------- 2. giáo viên
    t = Client()
    record("GV-00", "Giáo viên đăng nhập", t.login("gv.an@truong.edu.vn") == 200, "200")

    st, classes = t.json("/api/teacher/classes")
    record("GV-01a", "Danh sách lớp của giáo viên", st == 200 and len(classes["items"]) >= 3,
           f"{st} {len(classes['items'])} lớp")

    st, newcls = t.request("/api/teacher/classes", {"name": f"UAT {int(time.time())}", "grade": 8})
    st2, classes = t.json("/api/teacher/classes")
    code = next((k["join_code"] for k in classes["items"] if k["name"].startswith("UAT")), "")
    record("GV-01b", "Tạo lớp sinh mã 6 ký tự", st == 200 and len(code) == 6, f"{st} mã={code}")

    cls8 = next(k for k in classes["items"] if k["join_code"] == "8A1X21")
    st, roster = t.json(f"/api/teacher/classes/{cls8['id']}")
    record("GV-02a", "Xem danh sách học sinh của lớp", st == 200 and len(roster["roster"]) >= 5,
           f"{st} {len(roster['roster'])} học sinh")

    # Thêm học sinh: phải là tài khoản CHƯA ghi danh (học sinh tự đăng ký bằng mã lớp thì
    # đã vào lớp rồi, thêm lại sẽ bị từ chối đúng theo BR2 — nên dùng tài khoản do quản trị tạo).
    a_admin = Client()
    a_admin.login("admin@truong.edu.vn")
    loner = f"uat.loner.{int(time.time())}@truong.edu.vn"
    a_admin.request("/api/admin/users", {"email": loner, "full_name": "HS Chưa Vào Lớp",
                                        "role": "student", "password": PASSWORD})

    st, _ = t.request(f"/api/teacher/classes/{cls8['id']}/students", {"email": loner})
    st2, body2 = t.request(f"/api/teacher/classes/{cls8['id']}/students", {"email": loner})
    record("GV-02b", "Thêm học sinh chưa vào lớp; thêm lần hai bị từ chối",
           st == 200 and st2 == 422, f"lần 1={st} lần 2={st2}")

    cls10 = next((k for k in classes["items"] if k["join_code"] == "10A1X2"), None)
    if cls10:
        st3, _ = t.request(f"/api/teacher/classes/{cls10['id']}/students", {"email": loner})
        record("GV-03", "Học sinh đã ở lớp khác thì bị chặn (BR2)", st3 == 422, f"{st3}")

    past = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
    st, body = t.request(f"/api/teacher/classes/{cls8['id']}/assignments",
                         {"title": "UAT quá hạn", "lesson_id": lesson_id, "deadline": past,
                          "max_attempts": 1, "kind": "practice"})
    record("GV-04", "Hạn nộp trong quá khứ bị từ chối", st == 422, f"{st}")

    # Tạo một bài viết mới để hàng đợi chấm chắc chắn có bài (lượt chạy trước đã chấm hết).
    essay = ("My neighbourhood is quiet and green. There is a small market and a temple. "
             "People are friendly and the air is clean, so I like living here very much.")
    c.request(f"/api/writing/{lesson_id}/submit", {"text": essay})

    st, queue = t.json("/api/teacher/submissions")
    pending = queue["items"]
    record("GV-05a", "Hàng đợi chấm có bài", st == 200 and len(pending) >= 1, f"{st} {len(pending)} bài")

    if pending:
        sid = pending[0]["id"]
        st, body = t.json(f"/api/teacher/submissions/{sid}/grade",
                          data={"task": 1.0, "grammar": 1.0, "vocab": 1.0, "coherence": 1.0,
                                "comment": ""})
        record("GV-06", "Điểm < 5,0 mà thiếu nhận xét thì không lưu", st == 422, f"{st}")

        st, body = t.json(f"/api/teacher/submissions/{sid}/grade",
                          data={"task": 2.5, "grammar": 2.0, "vocab": 2.0, "coherence": 1.5,
                                "comment": "UAT: bài rõ ý."})
        record("GV-05b", "Chấm rubric và trả bài", st == 200 and body.get("final_score") is not None,
               f"{st} điểm cuối={body.get('final_score')}")

    st, _ = t.request(f"/api/teacher/classes/{cls8['id']}", method="GET")
    record("GV-07a", "Giáo viên mở đúng lớp của mình", st == 200, f"{st}")

    st, rep = t.json(f"/api/teacher/classes/{cls8['id']}/report")
    record("GV-08", "Báo cáo lớp có số liệu", st == 200 and rep.get("students", 0) >= 5,
           f"{st} {rep.get('students')} học sinh, TB lớp={rep.get('class_avg')}")

    st, csv_body = t.request(f"/reports/class/{cls8['id']}/export.csv")
    record("GV-08b", "Xuất CSV mở được, có tiêu đề", st == 200 and b"Email" in csv_body,
           f"{st} {len(csv_body)} bytes")

    # ---------------------------------------------------------------- 3. phụ huynh
    p = Client()
    pemail = f"uat.parent.{int(time.time())}@truong.edu.vn"
    st, _ = p.request("/api/auth/register-parent", {"email": pemail, "password": PASSWORD,
                                                    "full_name": "PH UAT"})
    record("PH-01a", "Phụ huynh tự đăng ký", st == 200, f"{st}")

    st, _ = p.request("/api/parent/link", {"student_email": fresh})
    record("PH-01b", "Gửi yêu cầu liên kết", st == 200, f"{st}")

    st, ch = p.json("/api/parent/children")
    ch_items = ch.get("items", [])
    pending_child = next((x for x in ch_items if x["status"] == "pending"), None)
    record("PH-01c", "Trạng thái chờ duyệt", pending_child is not None,
           f"{[x['status'] for x in ch_items]}")

    st, rep = p.json(f"/api/parent/report/{(pending_child or {}).get('student_id', 0)}")
    record("PH-02", "Chưa duyệt thì không xem được báo cáo (BR3)", st == 403, f"{st}")

    st, reqs = t.json("/api/teacher/parent-requests")
    mine = next((r for r in reqs["items"] if "UAT" in r["student"]), None)
    if mine:
        st, _ = t.request(f"/api/teacher/parent-requests/{mine['id']}", {"approve": True})
        record("PH-03a", "Giáo viên duyệt liên kết", st == 200, f"{st}")
        sid = pending_child["student_id"]
        st, rep = p.json(f"/api/parent/report/{sid}")
        record("PH-03b", "Sau khi duyệt xem được báo cáo",
               st == 200 and "skills" in rep, f"{st} phút học={rep.get('minutes')}")
        p.request(f"/api/parent/link/{sid}", method="DELETE")
        st2, _ = p.json(f"/api/parent/report/{sid}")
        record("PH-04", "Huỷ liên kết thì mất quyền ngay", st2 == 403, f"{st2}")

    # ---------------------------------------------------------------- 4. quản trị
    a = Client()
    record("QT-00", "Quản trị đăng nhập", a.login("admin@truong.edu.vn") == 200, "200")

    st, users = a.json("/api/admin/users")
    record("QT-01a", "Danh sách tài khoản", st == 200 and len(users["items"]) >= 10,
           f"{st} {len(users['items'])} tài khoản")

    temail = f"uat.teacher.{int(time.time())}@truong.edu.vn"
    st, _ = a.request("/api/admin/users", {"email": temail, "full_name": "GV UAT",
                                          "role": "teacher", "password": PASSWORD})
    record("QT-01b", "Tạo tài khoản giáo viên", st == 200, f"{st}")

    st, _ = a.request("/api/admin/users", {"email": temail, "full_name": "Trùng",
                                          "role": "teacher", "password": PASSWORD})
    record("QT-01c", "Tạo trùng email bị từ chối", st == 422, f"{st}")

    # khoá tài khoản vừa tạo rồi thử đăng nhập
    st, users = a.json("/api/admin/users?q=uat.teacher")
    target = users["items"][0]["id"]
    a.request(f"/api/admin/users/{target}/toggle", {})
    tc = Client()
    record("QT-02", "Khoá tài khoản thì không đăng nhập được", tc.login(temail) == 423,
           f"đăng nhập → {tc.login(temail)}")

    # import Excel: 2 dòng đúng + 1 dòng sai
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.append(["skill", "prompt", "option_a", "option_b", "option_c", "option_d",
               "correct_key", "explanation"])
    ws.append(["grammar", "UAT câu 1 ______ ok.", "is", "are", "be", "been", "A", ""])
    ws.append(["grammar", "UAT câu 2 ______ ok.", "is", "are", "be", "been", "B", ""])
    ws.append(["sai_skill", "UAT câu lỗi", "a", "b", "c", "d", "A", ""])
    buf = io.BytesIO()
    wb.save(buf)

    boundary = "----UAT"
    csrf = next((ck.value for ck in a.jar if ck.name == "csrf"), "")
    parts = [
        f'--{boundary}\r\nContent-Disposition: form-data; name="_csrf"\r\n\r\n{csrf}\r\n'.encode(),
        (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="uat.xlsx"\r\n'
         "Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\r\n\r\n").encode()
        + buf.getvalue() + b"\r\n",
        f"--{boundary}--\r\n".encode(),
    ]
    st, body = a.request(f"/api/admin/import-upload?lesson_id={lesson_id}",
                         raw=b"".join(parts), method="POST",
                         content_type=f"multipart/form-data; boundary={boundary}")
    data = json.loads(body) if st == 200 else {}
    record("QT-04", "Import Excel: nhận dòng đúng, báo dòng lỗi",
           st == 200 and data.get("added") == 2 and len(data.get("errors", [])) == 1,
           f"{st} thêm={data.get('added')} lỗi={len(data.get('errors', []))}")

    # ---------------------------------------------------------------- 5. phân quyền chéo
    s2 = Client()
    s2.login("an.nm@truong.edu.vn")
    st, _ = s2.request("/api/teacher/classes")
    record("SEC-03", "Học sinh không vào được API giáo viên", st == 403, f"{st}")

    # Lấy id một bài của khối 10 từ CSDL (API không cho học sinh lớp 8 liệt kê khối khác).
    import sqlite3

    db_path = Path(__file__).resolve().parent.parent / "data" / "app.db"
    grade10_lesson = None
    if db_path.exists():
        con = sqlite3.connect(db_path)
        row = con.execute("""SELECT l.id FROM lessons l JOIN units u ON u.id = l.unit_id
                             WHERE u.grade = 10 ORDER BY l.id LIMIT 1""").fetchone()
        con.close()
        grade10_lesson = row[0] if row else None

    if grade10_lesson:
        st, _ = s2.request(f"/api/lessons/{grade10_lesson}")
        record("SEC-04", "Học sinh lớp 8 không mở được bài lớp 10",
               st in (403, 404), f"lesson_id={grade10_lesson} → {st}")
    else:
        record("SEC-04", "Học sinh lớp 8 không mở được bài lớp 10", False,
               "không tìm thấy bài khối 10 trong CSDL")

    # ---------------------------------------------------------------- ghi báo cáo
    total = len(results)
    passed = sum(1 for r in results if r[2] == "PASS")
    lines = [
        "# Kết quả chạy kịch bản UAT (tự động qua HTTP)",
        "",
        f"- Thời điểm: {stamp}",
        f"- Lệnh: `.venv/bin/python scripts/run_uat.py`",
        f"- Kết quả: **{passed}/{total} PASS**",
        "",
        "| Mã | Kịch bản | Kết quả | Bằng chứng |",
        "|---|---|---|---|",
    ]
    for code, desc, kq, ev in results:
        lines.append(f"| {code} | {desc} | {kq} | {ev} |")

    lines += [
        "",
        "## Những gì script KHÔNG kiểm được (phải làm tay, ghi vào biên bản)",
        "",
        "| Mã | Việc | Cách làm |",
        "|---|---|---|",
        "| ST-10 | Ghi âm bằng micro trên điện thoại | `scripts/run_https.py`, mở `https://<IP-LAN>:8443` |",
        "| NF-01 | p95 ≤ 500 ms với 200 người | Locust trên staging, ghi p95 thật |",
        "| NF-04 | Cài lại từ đầu ≤ 10 phút | máy sạch, chạy README, bấm giờ |",
        "| UAT | 4 vai trò người thật dùng thử | `docs/UAT.md`, biên bản có chữ ký |",
        "",
        "> Script chạy trên CSDL phát triển và có tạo dữ liệu mới (học sinh/phụ huynh UAT).",
        "> Muốn CSDL sạch: `rm data/app.db` rồi `app.seed` → `app.content_pack` → `app.demo_data`.",
    ]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n{passed}/{total} PASS — đã ghi {OUT}")


if __name__ == "__main__":
    main()
