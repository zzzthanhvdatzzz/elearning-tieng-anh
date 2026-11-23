"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, ApiError, Me } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const me = await api<Me>("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      router.replace(me.role === "student" ? "/units" : "/assignments");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Không kết nối được tới server");
      setBusy(false);
    }
  }

  return (
    <>
      <h1>Đăng nhập</h1>
      {error && <div className="alert alert-error">{error}</div>}
      <form className="card form" onSubmit={submit}>
        <label>
          Email
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" />
        </label>
        <label>
          Mật khẩu
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required autoComplete="current-password" />
        </label>
        <button type="submit" disabled={busy}>{busy ? "Đang vào…" : "Đăng nhập"}</button>
      </form>
      <p className="muted">
        Chưa có tài khoản? <Link href="/register">Đăng ký bằng mã lớp</Link>
      </p>
    </>
  );
}
