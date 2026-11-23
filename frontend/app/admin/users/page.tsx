"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";

type Row = { id: number; email: string; full_name: string; role: string; active: boolean };
const LABEL: Record<string, string> = {
  student: "Học sinh", teacher: "Giáo viên", parent: "Phụ huynh", admin: "Quản trị",
};

export default function AdminUsersPage() {
  const router = useRouter();
  const [rows, setRows] = useState<Row[] | null>(null);
  const [roles, setRoles] = useState<string[]>([]);
  const [filter, setFilter] = useState({ role: "", q: "" });
  const [form, setForm] = useState({ email: "", full_name: "", role: "teacher", password: "" });
  const [error, setError] = useState("");
  const [flash, setFlash] = useState("");
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [total, setTotal] = useState(0);

  async function load() {
    try {
      const qs = new URLSearchParams({ role: filter.role, q: filter.q, page: String(page) }).toString();
      const d = await api<{ items: Row[]; roles: string[]; total: number; pages: number }>(`/api/admin/users?${qs}`);
      setRows(d.items);
      setRoles(d.roles);
      setTotal(d.total);
      setPages(d.pages);
    } catch (err) {
      if (err instanceof ApiError && (err.status === 401 || err.status === 403)) router.replace("/login");
      else setError("Lỗi tải danh sách tài khoản");
    }
  }
  useEffect(() => { load(); }, [filter.role, filter.q, page]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { setPage(1); }, [filter.role, filter.q]);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setError(""); setFlash("");
    try {
      await api("/api/admin/users", { method: "POST", body: JSON.stringify(form) });
      setFlash("Đã tạo tài khoản.");
      setForm({ email: "", full_name: "", role: "teacher", password: "" });
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Tạo tài khoản thất bại");
    }
  }

  async function toggle(id: number) {
    await api(`/api/admin/users/${id}/toggle`, { method: "POST" });
    load();
  }

  return (
    <>
      <h1>Tài khoản</h1>
      {flash && <div className="alert" style={{ background: "#e8f6ef", color: "#1b7f4b" }}>{flash}</div>}
      {error && <div className="alert alert-error">{error}</div>}

      <div className="card form">
        <h2>Tạo tài khoản</h2>
        <form onSubmit={create}>
          <label>Email <input type="email" value={form.email}
                 onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))} required /></label>
          <label>Họ tên <input value={form.full_name}
                 onChange={(e) => setForm((f) => ({ ...f, full_name: e.target.value }))} /></label>
          <label>Vai trò
            <select value={form.role} onChange={(e) => setForm((f) => ({ ...f, role: e.target.value }))}>
              {roles.map((r) => <option key={r} value={r}>{LABEL[r] ?? r}</option>)}
            </select>
          </label>
          <label>Mật khẩu ban đầu (≥ 8 ký tự)
            <input value={form.password} minLength={8} required
                   onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))} />
          </label>
          <button type="submit">Tạo tài khoản</button>
        </form>
      </div>

      <div className="card form">
        <label>Tìm theo email hoặc tên
          <input value={filter.q} onChange={(e) => setFilter((f) => ({ ...f, q: e.target.value }))} />
        </label>
        <label>Lọc vai trò
          <select value={filter.role} onChange={(e) => setFilter((f) => ({ ...f, role: e.target.value }))}>
            <option value="">— tất cả —</option>
            {roles.map((r) => <option key={r} value={r}>{LABEL[r] ?? r}</option>)}
          </select>
        </label>
      </div>

      {rows && (
        <table className="table">
          <thead><tr><th>Email</th><th>Họ tên</th><th>Vai trò</th><th>Trạng thái</th><th></th></tr></thead>
          <tbody>
            {rows.map((u) => (
              <tr key={u.id}>
                <td>{u.email}</td><td>{u.full_name || "—"}</td><td>{LABEL[u.role] ?? u.role}</td>
                <td>{u.active ? <span className="done">đang hoạt động</span> : <span className="wrong">đã khoá</span>}</td>
                <td>
                  <button type="button" className="link" onClick={() => toggle(u.id)}>
                    {u.active ? "Khoá" : "Mở khoá"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {rows && total > 0 && (
        <div className="row-between" style={{ marginTop: ".8rem" }}>
          <span className="muted">{total} tài khoản · trang {page}/{pages}</span>
          <span style={{ display: "flex", gap: ".5rem" }}>
            <button type="button" className="btn ghost sm" disabled={page <= 1}
                    onClick={() => setPage((p) => Math.max(1, p - 1))}>← Trước</button>
            <button type="button" className="btn ghost sm" disabled={page >= pages}
                    onClick={() => setPage((p) => Math.min(pages, p + 1))}>Sau →</button>
          </span>
        </div>
      )}
    </>
  );
}
