"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, ApiError, Me } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const [form, setForm] = useState({ full_name: "", email: "", password: "", join_code: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function set(key: keyof typeof form) {
    return (e: React.ChangeEvent<HTMLInputElement>) =>
      setForm((f) => ({ ...f, [key]: e.target.value }));
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api<Me>("/api/auth/register", { method: "POST", body: JSON.stringify(form) });
      router.replace("/units");     // AC1.3: đăng ký xong vào thẳng lộ trình
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Không kết nối được tới server");
      setBusy(false);
    }
  }

  return (
    <>
      <h1>Đăng ký học sinh</h1>
      <p className="muted">Cần mã lớp 6 ký tự do giáo viên cấp.</p>
      {error && <div className="alert alert-error">{error}</div>}
      <form className="card form" onSubmit={submit}>
        <label>Họ và tên
          <input value={form.full_name} onChange={set("full_name")} required />
        </label>
        <label>Email
          <input type="email" value={form.email} onChange={set("email")} required autoComplete="email" />
        </label>
        <label>Mật khẩu (tối thiểu 8 ký tự)
          <input type="password" value={form.password} onChange={set("password")} required minLength={8}
                 autoComplete="new-password" />
        </label>
        <label>Mã lớp
          <input value={form.join_code} onChange={set("join_code")} required maxLength={6}
                 style={{ textTransform: "uppercase" }} placeholder="VD: 8A1X21" />
        </label>
        <button type="submit" disabled={busy}>{busy ? "Đang tạo…" : "Tạo tài khoản"}</button>
      </form>
      <p className="muted">Đã có tài khoản? <Link href="/login">Đăng nhập</Link></p>
    </>
  );
}
