"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, Me } from "@/lib/api";

const ROLE_LABEL: Record<string, string> = {
  student: "Học sinh", teacher: "Giáo viên", parent: "Phụ huynh", admin: "Quản trị",
};

export default function Nav() {
  const [me, setMe] = useState<Me | null>(null);

  useEffect(() => {
    api<Me>("/api/me").then(setMe).catch(() => setMe(null));
  }, []);

  async function logout() {
    await api("/api/auth/logout", { method: "POST" });
    window.location.href = "/login";
  }

  return (
    <header className="topbar">
      <Link className="brand" href="/">English<span>Hub</span></Link>
      <nav>
        {me ? (
          <>
            {me.role === "student" && (
              <>
                <Link href="/units">Lộ trình</Link>
                <Link href="/assignments">Bài được giao</Link>
              </>
            )}
            <span className="who">{me.full_name || me.email} · {ROLE_LABEL[me.role] ?? me.role}</span>
            <button type="button" className="link" onClick={logout}>Đăng xuất</button>
          </>
        ) : (
          <>
            <Link href="/login">Đăng nhập</Link>
            <Link href="/register">Đăng ký</Link>
          </>
        )}
      </nav>
    </header>
  );
}
