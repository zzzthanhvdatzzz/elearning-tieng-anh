"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { api } from "@/lib/api";

type Item = { id: number; title: string; body: string; is_read: boolean; at: string };

export default function Bell({ unread }: { unread: number }) {
  const pathname = usePathname();
  const [count, setCount] = useState(unread);
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<Item[]>([]);

  useEffect(() => setCount(unread), [unread]);
  useEffect(() => setOpen(false), [pathname]);

  // Chuông tự cập nhật mỗi 30 giây và khi quay lại tab — để học sinh đang mở trang
  // vẫn thấy thông báo mới khi giáo viên vừa chấm bài, không phải F5.
  useEffect(() => {
    let alive = true;
    async function refresh() {
      if (document.visibilityState === "hidden") return;
      try {
        const data = await api<{ unread: number; items: Item[] }>("/api/notifications");
        if (!alive) return;
        setCount(data.unread);
        if (open) setItems(data.items);
      } catch {
        /* im lặng */
      }
    }
    const timer = setInterval(refresh, 30000);
    window.addEventListener("focus", refresh);
    document.addEventListener("visibilitychange", refresh);
    return () => {
      alive = false;
      clearInterval(timer);
      window.removeEventListener("focus", refresh);
      document.removeEventListener("visibilitychange", refresh);
    };
  }, [open]);

  async function toggle() {
    const next = !open;
    setOpen(next);
    if (!next) return;
    try {
      const data = await api<{ unread: number; items: Item[] }>("/api/notifications");
      setItems(data.items);
      setCount(data.unread);
    } catch {
      /* im lặng: không chặn thao tác chính khi API thông báo lỗi */
    }
  }

  async function markAll() {
    try {
      await api("/api/notifications/read", { method: "POST" });
      setItems((xs) => xs.map((x) => ({ ...x, is_read: true })));
      setCount(0);
    } catch {
      /* bỏ qua */
    }
  }

  return (
    <span style={{ position: "relative" }}>
      <button className="bell" onClick={toggle} aria-label={`Thông báo (${count} chưa đọc)`} aria-expanded={open}>
        🔔{count > 0 && <span className="bell-dot">{count > 9 ? "9+" : count}</span>}
      </button>
      {open && (
        <div className="bell-panel" role="dialog" aria-label="Danh sách thông báo">
          <div className="bell-head">
            <b>Thông báo</b>
            {count > 0 && <button className="linkish" onClick={markAll}>Đánh dấu đã đọc</button>}
          </div>
          {items.length === 0 ? (
            <p className="muted" style={{ padding: ".6rem .8rem" }}>Chưa có thông báo nào.</p>
          ) : (
            <ul className="bell-list">
              {items.map((n) => (
                <li key={n.id} className={n.is_read ? "" : "unread"}>
                  <b>{n.title}</b>
                  {n.body && <span>{n.body}</span>}
                  <em>{n.at}</em>
                </li>
              ))}
            </ul>
          )}
          <Link className="bell-foot" href="/notifications">Xem tất cả</Link>
        </div>
      )}
    </span>
  );
}
