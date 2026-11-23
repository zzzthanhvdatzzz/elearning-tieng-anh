"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";

export default function PasswordPage() {
  const router = useRouter();
  const [form, setForm] = useState({ old_password: "", new_password: "", confirm: "" });
  const [error, setError] = useState("");
  const [done, setDone] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(""); setDone("");
    if (form.new_password !== form.confirm) {
      setError("Mật khẩu nhập lại không khớp.");
      return;
    }
    try {
      const r = await api<{ message: string }>("/api/auth/password", {
        method: "POST",
        body: JSON.stringify({ old_password: form.old_password, new_password: form.new_password }),
      });
      setDone(r.message);
      setForm({ old_password: "", new_password: "", confirm: "" });
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) router.replace("/login");
      else setError(err instanceof ApiError ? err.message : "Đổi mật khẩu thất bại");
    }
  }

  return (
    <>
      <h1>Đổi mật khẩu</h1>
      {done && <div className="alert" style={{ background: "#e8f6ef", color: "#1b7f4b" }}>{done}</div>}
      {error && <div className="alert alert-error">{error}</div>}
      <div className="card form" style={{ maxWidth: 460 }}>
        <form onSubmit={submit}>
          <label>Mật khẩu hiện tại
            <input type="password" value={form.old_password} required autoComplete="current-password"
                   onChange={(e) => setForm((f) => ({ ...f, old_password: e.target.value }))} />
          </label>
          <label>Mật khẩu mới (≥ 8 ký tự)
            <input type="password" value={form.new_password} minLength={8} required autoComplete="new-password"
                   onChange={(e) => setForm((f) => ({ ...f, new_password: e.target.value }))} />
          </label>
          <label>Nhập lại mật khẩu mới
            <input type="password" value={form.confirm} minLength={8} required autoComplete="new-password"
                   onChange={(e) => setForm((f) => ({ ...f, confirm: e.target.value }))} />
          </label>
          <button type="submit">Đổi mật khẩu</button>
        </form>
        <p className="muted" style={{ marginTop: ".8rem" }}>
          Đổi xong, mọi thiết bị khác đang đăng nhập tài khoản này sẽ bị đăng xuất — trừ máy đang dùng.
        </p>
      </div>
    </>
  );
}
