"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, ApiError, Me } from "@/lib/api";

type Mode = "student" | "parent";

export default function RegisterPage() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("student");
  const [form, setForm] = useState({ full_name: "", email: "", password: "", join_code: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function set(key: keyof typeof form) {
    return (e: React.ChangeEvent<HTMLInputElement>) =>
      setForm((f) => ({ ...f, [key]: e.target.value }));
  }

  function switchMode(next: Mode) {
    setMode(next);
    setError("");
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      if (mode === "student") {
        await api<Me>("/api/auth/register", {
          method: "POST",
          body: JSON.stringify({
            full_name: form.full_name, email: form.email,
            password: form.password, join_code: form.join_code,
          }),
        });
        router.replace("/units");        // AC1.3: đăng ký xong vào thẳng lộ trình
      } else {
        await api<Me>("/api/auth/register-parent", {
          method: "POST",
          body: JSON.stringify({
            full_name: form.full_name, email: form.email, password: form.password,
          }),
        });
        router.replace("/parent");       // phụ huynh vào thẳng trang gửi yêu cầu liên kết
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Không kết nối được tới server");
      setBusy(false);
    }
  }

  const isStudent = mode === "student";

  return (
    <>
      <h1>Đăng ký tài khoản</h1>
      <div className="tabs" role="tablist" aria-label="Chọn loại tài khoản">
        <button type="button" role="tab" aria-selected={isStudent}
                className={isStudent ? "tab active" : "tab"}
                onClick={() => switchMode("student")}>
          Học sinh
        </button>
        <button type="button" role="tab" aria-selected={!isStudent}
                className={!isStudent ? "tab active" : "tab"}
                onClick={() => switchMode("parent")}>
          Phụ huynh
        </button>
      </div>

      <p className="muted">
        {isStudent
          ? "Cần mã lớp 6 ký tự do giáo viên cấp."
          : "Sau khi đăng ký, bạn gửi yêu cầu liên kết bằng email của con; giáo viên chủ nhiệm duyệt thì mới xem được báo cáo."}
      </p>

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
        {isStudent && (
          <label>Mã lớp
            <input value={form.join_code} onChange={set("join_code")} required maxLength={6}
                   style={{ textTransform: "uppercase" }} placeholder="VD: 8A1X21" />
          </label>
        )}
        <button type="submit" disabled={busy}>
          {busy ? "Đang tạo…" : isStudent ? "Tạo tài khoản học sinh" : "Tạo tài khoản phụ huynh"}
        </button>
      </form>

      <p className="muted">Đã có tài khoản? <Link href="/login">Đăng nhập</Link></p>
    </>
  );
}
