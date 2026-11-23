"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";

type Child = { student_id: number; name: string; status: string };

export default function ParentPage() {
  const router = useRouter();
  const [items, setItems] = useState<Child[] | null>(null);
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [flash, setFlash] = useState("");

  async function load() {
    try {
      const d = await api<{ items: Child[] }>("/api/parent/children");
      setItems(d.items);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) router.replace("/login");
      else setError(err instanceof ApiError ? err.message : "Lỗi tải dữ liệu");
    }
  }
  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function link(e: React.FormEvent) {
    e.preventDefault();
    setError(""); setFlash("");
    try {
      await api("/api/parent/link", { method: "POST", body: JSON.stringify({ student_email: email }) });
      setFlash("Đã gửi yêu cầu. Giáo viên duyệt thì bạn mới xem được báo cáo.");
      setEmail("");
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Gửi yêu cầu thất bại");
    }
  }

  async function unlink(id: number) {
    await api(`/api/parent/link/${id}`, { method: "DELETE" });
    load();
  }

  return (
    <>
      <h1>Báo cáo của con</h1>
      {flash && <div className="alert" style={{ background: "#e8f6ef", color: "#1b7f4b" }}>{flash}</div>}
      {error && <div className="alert alert-error">{error}</div>}

      <div className="card form">
        <h2>Liên kết với tài khoản của con</h2>
        <p className="muted">Nhập email học sinh; giáo viên bộ môn duyệt trước khi bạn xem dữ liệu (BR3).</p>
        <form onSubmit={link}>
          <label>Email của con
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required
                   placeholder="hs@truong.edu.vn" />
          </label>
          <button type="submit">Gửi yêu cầu liên kết</button>
        </form>
      </div>

      {items && items.length > 0 && (
        <div className="card">
          <h2>Các con ({items.length})</h2>
          <ul className="lesson-list">
            {items.map((c) => (
              <li key={c.student_id}>
                {c.status === "approved"
                  ? <Link href={`/parent/report/${c.student_id}`}>{c.name}</Link>
                  : <span>{c.name} <span className="muted">(chờ duyệt)</span></span>}
                {" "}
                <button type="button" className="link" onClick={() => unlink(c.student_id)}>Huỷ liên kết</button>
              </li>
            ))}
          </ul>
        </div>
      )}
      {items && items.length === 0 && <div className="card"><p className="muted">Chưa có liên kết nào.</p></div>}
    </>
  );
}
