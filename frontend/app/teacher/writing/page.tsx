"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";

type Row = {
  id: number; student: string; title: string; kind: string;
  words: number; has_audio: boolean; submitted_at: string;
};
type Detail = {
  id: number; kind: string; title: string; student: string; text: string;
  has_audio: boolean; words: number; status: string;
  criteria: string[]; labels: Record<string, string>;
};

export default function TeacherWritingPage() {
  const router = useRouter();
  const [rows, setRows] = useState<Row[] | null>(null);
  const [open, setOpen] = useState<Detail | null>(null);
  const [scores, setScores] = useState<Record<string, number>>({});
  const [comment, setComment] = useState("");
  const [error, setError] = useState("");
  const [flash, setFlash] = useState("");
  const [q, setQ] = useState("");

  async function load() {
    try {
      const d = await api<{ items: Row[] }>(`/api/teacher/submissions?q=${encodeURIComponent(q)}`);
      setRows(d.items);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) router.replace("/login");
      else if (err instanceof ApiError && err.status === 403) setError("Tài khoản này không phải giáo viên");
      else setError("Lỗi tải hàng đợi");
    }
  }

  useEffect(() => { load(); }, [q]); // eslint-disable-line react-hooks/exhaustive-deps

  async function openSubmission(id: number) {
    setFlash("");
    setError("");
    try {
      const d = await api<Detail>(`/api/teacher/submissions/${id}`);
      setOpen(d);
      const init: Record<string, number> = {};
      d.criteria.forEach((c) => { init[c] = 2; });
      setScores(init);
      setComment("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Lỗi mở bài");
    }
  }

  async function grade() {
    if (!open) return;
    setError("");
    try {
      const res = await api<{ final_score: number }>(`/api/teacher/submissions/${open.id}/grade`, {
        method: "POST",
        body: JSON.stringify({ ...scores, comment }),
      });
      setFlash(`Đã trả bài: ${res.final_score}/10`);
      setOpen(null);
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Lỗi chấm bài");
    }
  }

  if (error && !rows) return <div className="alert alert-error">{error}</div>;

  return (
    <>
      <h1>Chấm bài viết / bài nói</h1>
      {flash && <div className="alert" style={{ background: "#e8f6ef", color: "#1b7f4b" }}>{flash}</div>}
      {error && <div className="alert alert-error">{error}</div>}

      {open ? (
        <>
          <p><button type="button" className="link" onClick={() => setOpen(null)}>← Về hàng đợi</button></p>
          <div className="card">
            <h2>{open.student} — {open.title}</h2>
            <p className="muted">{open.words} từ{open.words < 40 && <span className="wrong"> · cảnh báo dưới 40 từ</span>}</p>
            {open.has_audio ? (
              <audio controls src={`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8010"}/audio/${open.id}`} />
            ) : (
              <blockquote className="essay-view" style={{ whiteSpace: "pre-wrap" }}>{open.text}</blockquote>
            )}
          </div>
          <div className="card form">
            <h2>Rubric — 4 tiêu chí, mỗi tiêu chí 0–2,5</h2>
            {open.criteria.map((c) => (
              <label key={c}>
                {open.labels[c] ?? c}
                <input type="number" min={0} max={2.5} step={0.5} value={scores[c] ?? 2}
                       onChange={(e) => setScores((s) => ({ ...s, [c]: Number(e.target.value) }))} />
              </label>
            ))}
            <label>
              Nhận xét (bắt buộc nếu tổng dưới 5,0)
              <textarea rows={4} value={comment} onChange={(e) => setComment(e.target.value)} />
            </label>
            <button type="button" className="btn" onClick={grade}>Trả bài cho học sinh</button>
          </div>
        </>
      ) : (
        <>
          {!rows && <p className="muted">Đang tải hàng đợi…</p>}
          {rows && rows.length === 0 && <div className="card"><p>Không có bài nào đang chờ chấm.</p></div>}
          {rows && rows.length > 0 && (
            <table className="table">
              <thead><tr><th>Học sinh</th><th>Bài</th><th>Loại</th><th>Số từ</th><th></th></tr></thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.id}>
                    <td>{r.student}</td>
                    <td>{r.title}</td>
                    <td>{r.kind === "speaking" ? "Nói" : "Viết"}</td>
                    <td>{r.has_audio ? "—" : r.words}</td>
                    <td><button type="button" className="link" onClick={() => openSubmission(r.id)}>Chấm →</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}
    </>
  );
}
