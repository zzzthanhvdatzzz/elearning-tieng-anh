"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";

type Row = {
  id: number; student: string; klass: string; lesson: string; status: string;
  attempt_no: number; score: number | null; late_days: number; at: string; has_audio: boolean;
};

export default function SpeakingQueuePage() {
  const router = useRouter();
  const [rows, setRows] = useState<Row[] | null>(null);
  const [showGraded, setShowGraded] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api<{ items: Row[] }>(`/api/teacher/speaking?only_pending=${!showGraded}`)
      .then((d) => setRows(d.items))
      .catch((e) => {
        if (e instanceof ApiError && (e.status === 401 || e.status === 403)) router.replace("/login");
        else setError("Lỗi tải hàng đợi bài nói");
      });
  }, [showGraded, router]);

  return (
    <>
      <div className="row-between">
        <h1>Chấm bài nói</h1>
        <label className="muted" style={{ display: "flex", gap: ".4rem", alignItems: "center" }}>
          <input type="checkbox" checked={showGraded}
                 onChange={(e) => setShowGraded(e.target.checked)} style={{ width: "auto" }} />
          Hiện cả bài đã chấm
        </label>
      </div>
      {error && <div className="alert alert-error">{error}</div>}
      {!rows && <p className="muted">Đang tải…</p>}
      {rows && rows.length === 0 && (
        <div className="card"><p className="muted">Không có bài nói nào đang chờ chấm.</p></div>
      )}
      {rows && rows.length > 0 && (
        <table className="table">
          <thead>
            <tr><th>Học sinh</th><th>Lớp</th><th>Bài</th><th>Lượt</th><th>Nộp lúc</th><th></th></tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td>{r.student}</td>
                <td>{r.klass}</td>
                <td>{r.lesson}</td>
                <td>{r.attempt_no}{r.late_days ? <span className="wrong"> · trễ {r.late_days} ngày</span> : null}</td>
                <td>{r.at}</td>
                <td>
                  {r.status === "graded"
                    ? <span className="done">{r.score}/10</span>
                    : <Link className="btn ghost sm" href={`/teacher/speaking/${r.id}`}>Nghe &amp; chấm</Link>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}
