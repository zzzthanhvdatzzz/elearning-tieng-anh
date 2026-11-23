"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";

type State = {
  lesson: { id: number; title: string }; prompt: string; min_words: number;
  attempts_left: number; max_attempts: number;
  last: { id: number; text: string; status: string; score: number | null } | null;
};
type Result = {
  submission: { id: number; text: string; status: string; score: number | null; attempt_no: number } | null;
  rubric: Record<string, number>; feedback: string; labels: Record<string, string>;
  attempts_left: number;
};

const DRAFT_KEY = (id: string) => `draft-writing-${id}`;

export default function WritingView({ lessonId }: { lessonId: string }) {
  const router = useRouter();
  const [state, setState] = useState<State | null>(null);
  const [result, setResult] = useState<Result | null>(null);
  const [text, setText] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api<State>(`/api/writing/${lessonId}`)
      .then((s) => {
        setState(s);
        const saved = localStorage.getItem(DRAFT_KEY(lessonId));
        setText(saved || (s.last && s.last.status !== "graded" ? s.last.text : ""));
      })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) router.replace("/login");
        else setError(err instanceof ApiError ? err.message : "Lỗi tải đề");
      });
  }, [lessonId, router]);

  // AC8.1: tự lưu nháp mỗi 10 giây
  useEffect(() => {
    const id = setInterval(() => localStorage.setItem(DRAFT_KEY(lessonId), text), 10000);
    return () => clearInterval(id);
  }, [lessonId, text]);

  const words = text.trim() ? text.trim().split(/\s+/).length : 0;

  async function submit() {
    setBusy(true);
    setError("");
    try {
      await api(`/api/writing/${lessonId}/submit`, { method: "POST", body: JSON.stringify({ text }) });
      localStorage.removeItem(DRAFT_KEY(lessonId));
      const res = await api<Result>(`/api/writing/${lessonId}/result`);
      setResult(res);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Nộp bài thất bại");
    } finally {
      setBusy(false);
    }
  }

  if (error && !state) return <div className="alert alert-error">{error}</div>;
  if (!state) return <p className="muted">Đang tải…</p>;

  if (result?.submission) {
    const s = result.submission;
    return (
      <>
        <p className="muted"><Link href={`/lesson/${lessonId}`}>← Về bài học</Link></p>
        <h1>Bài viết của tôi</h1>
        <div className="card">
          <p className="muted">Lượt {s.attempt_no}</p>
          <blockquote className="essay-view" style={{ whiteSpace: "pre-wrap" }}>{s.text}</blockquote>
        </div>
        {s.score !== null ? (
          <>
            <div className="card score-card">
              <p className="score">{s.score}<span>/10</span></p>
              <p className="muted">Điểm do giáo viên chấm theo 4 tiêu chí</p>
            </div>
            <div className="card">
              <h2>Nhận xét của giáo viên</h2>
              <table className="table">
                <thead><tr><th>Tiêu chí</th><th>Điểm (0–2,5)</th></tr></thead>
                <tbody>
                  {Object.entries(result.rubric).map(([c, v]) => (
                    <tr key={c}><td>{result.labels[c] ?? c}</td><td>{v}</td></tr>
                  ))}
                </tbody>
              </table>
              {result.feedback && <p className="explain">{result.feedback}</p>}
            </div>
          </>
        ) : (
          <div className="card"><p><strong>Đang chờ giáo viên chấm.</strong></p></div>
        )}
      </>
    );
  }

  return (
    <>
      <p className="muted"><Link href={`/lesson/${lessonId}`}>← Về bài học</Link></p>
      <h1>Luyện viết: {state.lesson.title}</h1>
      <p className="muted">Lượt còn {state.attempts_left}/{state.max_attempts}</p>
      {error && <div className="alert alert-error">{error}</div>}

      <div className="card">
        <h2>Đề bài</h2>
        <p>{state.prompt}</p>
        <p className="muted">Tối thiểu {state.min_words} từ. Nháp tự lưu trên máy này mỗi 10 giây.</p>
      </div>

      <div className="card form">
        <textarea rows={12} value={text} onChange={(e) => setText(e.target.value)}
                  placeholder="Write your paragraph here..." />
        <p className="muted">
          Số từ: {words}
          {words < state.min_words && <span className="wrong"> (dưới {state.min_words} từ, giáo viên sẽ nhắc)</span>}
        </p>
        <button type="button" className="btn" onClick={submit} disabled={busy || words < 20}>
          {busy ? "Đang nộp…" : "Nộp bài"}
        </button>
      </div>
    </>
  );
}
