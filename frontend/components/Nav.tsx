"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { api, Me } from "@/lib/api";
import Bell from "@/components/Bell";

const ROLE_LABEL: Record<string, string> = {
  student: "Học sinh", teacher: "Giáo viên", parent: "Phụ huynh", admin: "Quản trị",
};

export default function Nav() {
  const [me, setMe] = useState<Me | null>(null);
  const pathname = usePathname();

  useEffect(() => {
    api<Me>("/api/me").then(setMe).catch(() => setMe(null));
  }, [pathname]);

  async function logout() {
    await api("/api/auth/logout", { method: "POST" });
    window.location.href = "/login";
  }

  const name = me ? (me.full_name || me.email) : "";
  const initial = name.trim().charAt(0).toUpperCase();
  const cls = (href: string) => (pathname === href || pathname.startsWith(`${href}/`) ? "active" : "");

  return (
    <header className="topbar">
      <Link className="brand" href="/">English<span>Hub</span></Link>
      <nav>
        {me ? (
          <>
            <Link className={cls("/dashboard")} href="/dashboard">Tổng quan</Link>
            {me.role === "student" && (
              <>
                <Link className={cls("/units")} href="/units">Lộ trình</Link>
                <Link className={cls("/assignments")} href="/assignments">Bài được giao</Link>
                <Link className={cls(`/reports/student/${me.id}`)} href={`/reports/student/${me.id}`}>Báo cáo</Link>
              </>
            )}
            {me.role === "teacher" && (
              <>
                <Link className={cls("/teacher/classes")} href="/teacher/classes">Lớp</Link>
                <Link className={cls("/teacher/writing")} href="/teacher/writing">Chấm bài viết</Link>
                <Link className={cls("/teacher/speaking")} href="/teacher/speaking">Chấm bài nói</Link>
                <Link className={cls("/teacher/videos")} href="/teacher/videos">Video bài giảng</Link>
                <Link className={cls("/teacher/parents")} href="/teacher/parents">Phụ huynh</Link>
              </>
            )}
            {me.role === "parent" && <Link className={cls("/parent")} href="/parent">Báo cáo của con</Link>}
            {me.role === "admin" && (
              <>
                <Link className={cls("/admin/users")} href="/admin/users">Tài khoản</Link>
                <Link className={cls("/admin/import")} href="/admin/import">Import</Link>
                <Link className={cls("/admin/audit")} href="/admin/audit">Nhật ký</Link>
              </>
            )}
            <Link className={cls("/settings/password")} href="/settings/password">Mật khẩu</Link>
            <span className="who">
              <span className="avatar" aria-hidden>{initial}</span>
              {name} · {ROLE_LABEL[me.role] ?? me.role}
            </span>
            <Bell unread={me.unread ?? 0} />
            <button type="button" className="link" onClick={logout}>Đăng xuất</button>
          </>
        ) : (
          <>
            <Link className={cls("/login")} href="/login">Đăng nhập</Link>
            <Link className={cls("/register")} href="/register">Đăng ký</Link>
          </>
        )}
      </nav>
    </header>
  );
}
