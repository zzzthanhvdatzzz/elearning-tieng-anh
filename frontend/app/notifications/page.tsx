"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";

type Item = { id: number; title: string; body: string; is_read: boolean; at: string };

export default function Notifications() {
  const router = useRouter();
  const [items, setItems] = useState<Item[] | null>(null);
  const [error, setError] = useState("");

  function load() {
    api<{ unread: number; items: Item[] }>("/api/notifications")
      .then((d) => setItems(d.items))
      .catch((e) => {
        if (e instanceof ApiError && e.status === 401) router.replace("/login");
        else setError("Không tải được thông báo.");
      });
  }

  useEffect(load, [router]);

  async function markAll() {
    await api("/api/notifications/read", { method: "POST" });
    load();
  }

  if (error) return <div className="alert alert-error">{error}</div>;
  if (!items) return <p className="muted">Đang tải…</p>;

  return (
    <>
      <div className="row-between">
        <h1>Thông báo</h1>
        {items.some((n) => !n.is_read) && (
          <button className="btn ghost" onClick={markAll}>Đánh dấu tất cả đã đọc</button>
        )}
      </div>
      {items.length === 0 ? (
        <div className="card"><p className="muted">Chưa có thông báo nào. Khi giáo viên giao bài hoặc trả điểm, thông báo sẽ xuất hiện ở đây.</p></div>
      ) : (
        <div className="card">
          <ul className="notice-list">
            {items.map((n) => (
              <li key={n.id} className={n.is_read ? "read" : "unread"}>
                <div><b>{n.title}</b>{!n.is_read && <span className="pill">mới</span>}</div>
                {n.body && <p>{n.body}</p>}
                <em>{n.at}</em>
              </li>
            ))}
          </ul>
        </div>
      )}
    </>
  );
}
