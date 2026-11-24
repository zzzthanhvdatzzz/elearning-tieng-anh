"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";

type Klass = { id: number; name: string; grade: number; join_code: string; students: number };
type Detail = {
  klass: { id: number; name: string; grade: number; join_code: string };
  roster: { id: number; name: string; email: string; cefr: string | null }[];
  lessons: { id: number; code: string; title: string }[];
  assignments: { id: number; title: string; kind: string; deadline: string | null; max_attempts: number }[];
};

export default function TeacherClassesPage() {
  const router = useRouter();
  const [items, setItems] = useState<Klass[] | null>(null);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [form, setForm] = useState({ name: "", grade: "8" });
  const [studentEmail, setStudentEmail] = useState("");
  const [asg, setAsg] = useState({ title: "", lesson_id: "", deadline: "", max_attempts: "3", kind: "practice" });
  const [error, setError] = useState("");
  const [flash, setFlash] = useState("");

  function handle(err: unknown, fallback: string) {
    if (err instanceof ApiError && (err.status === 401 || err.status === 403)) router.replace("/login");
    else setError(err instanceof ApiError ? err.message : fallback);
  }

  async function load() {
    try {
      const d = await api<{ items: Klass[] }>("/api/teacher/classes");
      setItems(d.items);
    } catch (err) { handle(err, "Lỗi tải danh sách lớp"); }
  }
  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function open(id: number) {
    setError(""); setFlash("");
    try {
      const d = await api<Detail>(`/api/teacher/classes/${id}`);
      setDetail(d);
      setAsg((a) => ({ ...a, lesson_id: d.lessons[0] ? String(d.lessons[0].id) : "" }));
    } catch (err) { handle(err, "Lỗi mở lớp"); }
  }

  async function createClass(e: React.FormEvent) {
    e.preventDefault();
    setError(""); setFlash("");
    try {
      await api("/api/teacher/classes", { method: "POST", body: JSON.stringify(form) });
      setFlash("Đã tạo lớp và sinh mã tham gia.");
      setForm({ name: "", grade: "8" });
      load();
    } catch (err) { handle(err, "Tạo lớp thất bại"); }
  }

  async function addStudent(e: React.FormEvent) {
    e.preventDefault();
    if (!detail) return;
    setError(""); setFlash("");
    try {
      await api(`/api/teacher/classes/${detail.klass.id}/students`,
        { method: "POST", body: JSON.stringify({ email: studentEmail }) });
      setFlash("Đã thêm học sinh vào lớp.");
      setStudentEmail("");
      open(detail.klass.id);
    } catch (err) { handle(err, "Thêm học sinh thất bại"); }
  }

  async function removeStudent(id: number) {
    if (!detail) return;
    await api(`/api/teacher/classes/${detail.klass.id}/students/${id}`, { method: "DELETE" });
    open(detail.klass.id);
  }

  async function createAssignment(e: React.FormEvent) {
    e.preventDefault();
    if (!detail) return;
    setError(""); setFlash("");
    try {
      await api(`/api/teacher/classes/${detail.klass.id}/assignments`, {
        method: "POST",
        body: JSON.stringify({ ...asg, max_attempts: Number(asg.max_attempts) }),
      });
      setFlash("Đã giao bài cho lớp.");
      setAsg((a) => ({ ...a, title: "", deadline: "" }));
      open(detail.klass.id);
    } catch (err) { handle(err, "Giao bài thất bại"); }
  }

  return (
    <>
      <h1>Lớp của tôi</h1>
      {flash && <div className="alert" style={{ background: "#e8f6ef", color: "#1b7f4b" }}>{flash}</div>}
      {error && <div className="alert alert-error">{error}</div>}

      {!detail && (
        <>
          <div className="card form">
            <h2>Tạo lớp mới</h2>
            <form onSubmit={createClass}>
              <label>Tên lớp
                <input value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                       required placeholder="VD: 8A3 — Tiếng Anh" />
              </label>
              <label>Khối
                <select value={form.grade} onChange={(e) => setForm((f) => ({ ...f, grade: e.target.value }))}>
                  <option value="8">Khối 8 (THCS)</option>
                  <option value="10">Khối 10 (THPT)</option>
                </select>
              </label>
              <button type="submit">Tạo lớp và sinh mã</button>
            </form>
          </div>

          {items && items.length === 0 && <div className="card"><p>Bạn chưa có lớp nào.</p></div>}
          {items && items.length > 0 && (
            <table className="table">
              <thead><tr><th>Lớp</th><th>Khối</th><th>Mã tham gia</th><th>Học sinh</th><th></th></tr></thead>
              <tbody>
                {items.map((k) => (
                  <tr key={k.id}>
                    <td>{k.name}</td><td>{k.grade}</td>
                    <td><code>{k.join_code}</code></td><td>{k.students}</td>
                    <td><button type="button" className="link" onClick={() => open(k.id)}>Quản lý →</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}

      {detail && (
        <>
          <p>
            <button type="button" className="link"
                    onClick={() => { setDetail(null); load(); }}>← Về danh sách lớp</button>
          </p>
          <h2>{detail.klass.name}</h2>
          <p>Mã tham gia: <code>{detail.klass.join_code}</code>{" "}
            <span className="muted">— học sinh tự đăng ký bằng mã này</span></p>
          <p><Link className="btn" href={`/teacher/classes/${detail.klass.id}/report`}>Xem báo cáo lớp →</Link></p>

          <div className="card form">
            <h2>Thêm học sinh</h2>
            <form onSubmit={addStudent}>
              <label>Email học sinh (em đó phải tự đăng ký trước)
                <input type="email" value={studentEmail} onChange={(e) => setStudentEmail(e.target.value)}
                       required placeholder="hs@truong.edu.vn" />
              </label>
              <button type="submit">Thêm vào lớp</button>
            </form>
          </div>

          <div className="card">
            <h2>Danh sách ({detail.roster.length})</h2>
            {detail.roster.length === 0 ? <p className="muted">Chưa có học sinh nào.</p> : (
              <table className="table">
                <thead><tr><th>Họ tên</th><th>Email</th><th>CEFR</th><th></th></tr></thead>
                <tbody>
                  {detail.roster.map((r) => (
                    <tr key={r.id}>
                      <td>{r.name}</td><td>{r.email}</td><td>{r.cefr ?? "chưa xếp"}</td>
                      <td>
                        <button type="button" className="link"
                                onClick={() => removeStudent(r.id)}>Xoá khỏi lớp</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <div className="card form">
            <h2>Giao bài</h2>
            <form onSubmit={createAssignment}>
              <label>Tên bài giao
                <input value={asg.title} onChange={(e) => setAsg((a) => ({ ...a, title: e.target.value }))}
                       required placeholder="VD: Luyện tập Unit 1 — L1" />
              </label>
              <label>Bài học
                <select value={asg.lesson_id} onChange={(e) => setAsg((a) => ({ ...a, lesson_id: e.target.value }))}>
                  <option value="">— Không gắn bài học —</option>
                  {detail.lessons.map((l) => (
                    <option key={l.id} value={l.id}>{l.code} — {l.title}</option>
                  ))}
                </select>
              </label>
              <label>Loại
                <select value={asg.kind} onChange={(e) => setAsg((a) => ({ ...a, kind: e.target.value }))}>
                  <option value="practice">Trắc nghiệm (chấm tự động)</option>
                  <option value="writing">Bài viết (giáo viên chấm rubric)</option>
                </select>
              </label>
              <label>Hạn nộp (giờ Việt Nam)
                <input type="datetime-local" value={asg.deadline}
                       onChange={(e) => setAsg((a) => ({ ...a, deadline: e.target.value }))} />
              </label>
              <label>Số lần làm tối đa
                <input type="number" min={1} max={10} value={asg.max_attempts}
                       onChange={(e) => setAsg((a) => ({ ...a, max_attempts: e.target.value }))} />
              </label>
              <button type="submit">Giao bài cho lớp</button>
            </form>
          </div>

          <div className="card">
            <h2>Bài đã giao ({detail.assignments.length})</h2>
            {detail.assignments.length === 0 ? <p className="muted">Chưa giao bài nào.</p> : (
              <table className="table">
                <thead><tr><th>Bài</th><th>Loại</th><th>Hạn</th><th>Lượt</th></tr></thead>
                <tbody>
                  {detail.assignments.map((a) => (
                    <tr key={a.id}>
                      <td>{a.title}</td>
                      <td>{a.kind === "writing" ? "Viết" : a.kind === "speaking" ? "Nói" : a.kind === "placement" ? "Kiểm tra đầu vào" : "Trắc nghiệm"}</td>
                      <td>{a.deadline ? new Date(a.deadline).toLocaleString("vi-VN") : "—"}</td>
                      <td>{a.max_attempts}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}
    </>
  );
}
