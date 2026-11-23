"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";

type Todo = {
  id: number; title: string; kind: string; lesson_id: number | null;
  deadline: string | null; max_attempts: number;
  attempts_used: number; attempts_left: number; best: number | null; overdue: boolean;
};

export default function AssignmentsPage() {
  const router = useRouter();
  const [items, setItems] = useState<Todo[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<{ items: Todo[] }>("/api/assignments")
      .then((d) => setItems(d.items))
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) router.replace("/login");
        else setError(err instanceof ApiError ? err.message : "Lỗi tải danh sách");
      });
  }, [router]);

  if (error) return <div className="alert alert-error">{error}</div>;
  if (!items) return <p className="muted">Đang tải…</p>;

  return (
    <>
      <h1>Bài được giao</h1>
      {items.length === 0 ? (
        <div className="card"><p>Chưa có bài nào được giao cho lớp của bạn.</p></div>
      ) : (
        <table className="table">
          <thead>
            <tr><th>Bài</th><th>Hạn nộp</th><th>Lượt</th><th>Điểm cao nhất</th><th></th></tr>
          </thead>
          <tbody>
            {items.map((t) => (
              <tr key={t.id}>
                <td>{t.title}</td>
                <td>
                  {t.deadline ? new Date(t.deadline).toLocaleString("vi-VN") : <span className="muted">không hạn</span>}
                  {t.overdue && t.best === null && <span className="wrong"> (quá hạn)</span>}
                </td>
                <td>{t.attempts_used}/{t.max_attempts}</td>
                <td>{t.best ?? "—"}</td>
                <td>
                  {t.lesson_id && (
                    <Link href={t.kind === "writing" ? `/lesson/${t.lesson_id}` : `/practice/${t.lesson_id}`}>
                      Làm bài →
                    </Link>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}
