"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";

type Klass = { id: number; name: string; grade: number; join_code: string; students: number };

export default function TeacherClassesPage() {
  const router = useRouter();
  const [items, setItems] = useState<Klass[] | null>(null);
  const [form, setForm] = useState({ name: "", grade: "8" });
  const [error, setError] = useState("");
  const [flash, setFlash] = useState("");

  async function load() {
    try {
      const d = await api<{ items: Klass[] }>("/api/teacher/classes");
      setItems(d.items);
    } catch (err) {
      if (err instanceof ApiError && (err.status === 401 || err.status === 403)) router.replace("/login");
      else setError("Lỗi tải danh sách lớp");
    }
  }
  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await api("/api/teacher/classes", { method: "POST", body: JSON.stringify(form) });
      setFlash("Đã tạo lớp và sinh mã tham gia.");
      setForm({ name: "", grade: "8" });
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Tạo lớp thất bại");
    }
  }

  return (
    <>
      <h1>Lớp của tôi</h1>
      {flash && <div className="alert" style={{ background: "#e8f6ef", color: "#1b7f4b" }}>{flash}</div>}
      {error && <div className="alert alert-error">{error}</div>}

      <div className="card form">
        <h2>Tạo lớp mới</h2>
        <form onSubmit={create}>
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
          <thead><tr><th>Lớp</th><th>Khối</th><th>Mã tham gia</th><th>Học sinh</th></tr></thead>
          <tbody>
            {items.map((k) => (
              <tr key={k.id}>
                <td>{k.name}</td><td>{k.grade}</td>
                <td><code>{k.join_code}</code></td><td>{k.students}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <p className="muted">
        Quản lý danh sách học sinh, giao bài và xem báo cáo lớp: dùng bản giao diện đầy đủ ở
        <code> /teacher/classes/{"{id}"}</code> của backend (cổng 8010) — phần này đang được chuyển tiếp.
      </p>
    </>
  );
}
