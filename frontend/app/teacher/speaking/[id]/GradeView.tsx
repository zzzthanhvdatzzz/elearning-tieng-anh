"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { API, api, ApiError } from "@/lib/api";

type Detail = {
  id: number; status: string; attempt_no: number; student: string; lesson: string;
  audio: string | null; audio_name: string | null; score: number | null; late_days: number;
  deadline: string | null; criteria: string[]; labels: Record<string, string>;
  rubric: Record<string, number>; feedback: string;
};

export default function GradeView({ submissionId }: { submissionId: string }) {
  const router = useRouter();
  const [d, setD] = useState<Detail | null>(null);
  const [scores, setScores] = useState<Record<string, string>>({});
  const [comment, setComment] = useState("");
  const [error, setError] = useState("");
  const [flash, setFlash] = useState("");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);

  function load() {
    api<Detail>(`/api/teacher/speaking/${submissionId}`)
      .then((data) => {
        setD(data);
        setScores(Object.fromEntries(data.criteria.map((c) => [c, String(data.rubric[c] ?? "")])));
        setComment(data.feedback ?? "");
      })
      .catch((e) => {
        if (e instanceof ApiError && (e.status === 401 || e.status === 403)) router.replace("/login");
        else setError("Không tải được bài nói này");
      });
  }
  useEffect(load, [submissionId]); // eslint-disable-line react-hooks/exhaustive-deps

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(""); setFlash(""); setBusy(true);
    try {
      const body: Record<string, unknown> = { comment };
      if (d) for (const c of d.criteria) body[c] = Number(scores[c] || 0);
      const r = await api<{ final_score: number }>(`/api/teacher/speaking/${submissionId}/grade`, {
        method: "POST", body: JSON.stringify(body),
      });
      setFlash(`Đã chấm: ${r.final_score}/10`);
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Chấm thất bại");
    } finally {
      setBusy(false);
    }
  }

  async function reopen() {
    setError(""); setFlash(""); setBusy(true);
    try {
      await api(`/api/teacher/submissions/${submissionId}/reopen`, {
        method: "POST", body: JSON.stringify({ reason }),
      });
      setFlash("Đã mở lại bài. Chấm lại bên dưới.");
      setReason("");
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Không mở lại được");
    } finally {
      setBusy(false);
    }
  }

  if (error && !d) return <div className="alert alert-error">{error}</div>;
  if (!d) return <p className="muted">Đang tải…</p>;

  const graded = d.status === "graded";

  return (
    <>
      <p className="muted"><Link href="/teacher/speaking">← Hàng đợi bài nói</Link></p>
      <h1>{d.student}</h1>
      <p className="muted">{d.lesson} · lượt {d.attempt_no}
        {d.deadline ? ` · hạn ${d.deadline}` : ""}{d.late_days ? ` · nộp trễ ${d.late_days} ngày` : ""}</p>

      {flash && <div className="alert" style={{ background: "#e8f6ef", color: "#1b7f4b" }}>{flash}</div>}
      {error && <div className="alert alert-error">{error}</div>}

      <div className="card">
        <h2>Nghe bài nói</h2>
        {d.audio ? (
          <>
            <audio controls preload="none" src={`${API}${d.audio}`} style={{ width: "100%" }}>
              Trình duyệt không phát được tệp này.
            </audio>
            <p className="muted">Tệp: {d.audio_name} · chỉ bạn và chính học sinh nghe được.</p>
          </>
        ) : (
          <p className="muted">Bài này không có tệp ghi âm.</p>
        )}
      </div>

      {graded ? (
        <div className="card">
          <h2>Bài đã chấm — {d.score}/10</h2>
          <p className="muted">Muốn sửa điểm phải mở lại và ghi lý do (lưu vào nhật ký).</p>
          <label className="muted" style={{ display: "block", marginBottom: ".5rem" }}>
            <input value={reason} onChange={(e) => setReason(e.target.value)}
                   placeholder="Lý do mở lại (ít nhất 10 ký tự)"
                   style={{ width: "100%", marginTop: ".3rem", padding: ".6rem" }} />
          </label>
          <button className="btn ghost" onClick={reopen} disabled={busy || reason.trim().length < 10}>
            Mở lại để chấm lại
          </button>
        </div>
      ) : (
        <form className="card form" onSubmit={submit}>
          <h2>Chấm 4 tiêu chí (0 – 2,5 mỗi tiêu chí)</h2>
          {d.criteria.map((c) => (
            <label key={c}>{d.labels[c]}
              <input type="number" step="0.25" min="0" max="2.5" required
                     value={scores[c] ?? ""}
                     onChange={(e) => setScores((s) => ({ ...s, [c]: e.target.value }))} />
            </label>
          ))}
          <label>Nhận xét cho học sinh (bắt buộc nếu điểm dưới 5)
            <textarea rows={4} value={comment} onChange={(e) => setComment(e.target.value)} />
          </label>
          <button type="submit" disabled={busy}>{busy ? "Đang lưu…" : "Lưu điểm"}</button>
        </form>
      )}
    </>
  );
}
