"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";

type Question = { id: number; prompt: string; options: string[] };
type Exam = {
  lesson: { id: number; title: string };
  attempts_left: number; max_attempts: number; questions: Question[];
};
type Result = {
  score: number; correct: number; total: number; attempts_left: number;
  review: { question_id: number; prompt: string; chosen: string; correct_key: string;
            is_correct: boolean; explanation: string }[];
};

const LETTERS = ["A", "B", "C", "D"];

export default function PracticeView({ lessonId }: { lessonId: string }) {
  const router = useRouter();
  const [exam, setExam] = useState<Exam | null>(null);
  const [result, setResult] = useState<Result | null>(null);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api<Exam>(`/api/practice/${lessonId}`)
      .then(setExam)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) router.replace("/login");
        else setError(err instanceof ApiError ? err.message : "Lỗi tải đề");
      });
  }, [lessonId, router]);

  async function submit() {
    setBusy(true);
    setError("");
    try {
      const res = await api<Result>(`/api/practice/${lessonId}/submit`, {
        method: "POST",
        body: JSON.stringify({ answers }),
      });
      setResult(res);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Nộp bài thất bại");
    } finally {
      setBusy(false);
    }
  }

  if (error && !exam) return <div className="alert alert-error">{error}</div>;
  if (!exam) return <p className="muted">Đang tải đề…</p>;

  if (result) {
    return (
      <>
        <p className="muted"><Link href={`/lesson/${lessonId}`}>← Về bài học</Link></p>
        <h1>Kết quả luyện tập</h1>
        <div className="card score-card">
          <p className="score">{result.score}<span>/10</span></p>
          <p className="muted">
            Đúng {result.correct}/{result.total} câu · còn {result.attempts_left} lượt
          </p>
        </div>
        <div className="card">
          <h2>Xem lại từng câu</h2>
          {result.review.map((r, i) => (
            <div key={r.question_id} className={`q review ${r.is_correct ? "ok" : "bad"}`}>
              <p><b>{i + 1}.</b> {r.prompt}</p>
              <p className="muted">
                Bạn chọn: <b>{r.chosen || "—"}</b> · Đáp án đúng: <b className="done">{r.correct_key}</b>
                {r.is_correct ? <span className="done"> ✓ đúng</span> : <span className="wrong"> ✗ sai</span>}
              </p>
              {r.explanation && <p className="explain">Giải thích: {r.explanation}</p>}
            </div>
          ))}
        </div>
        {result.attempts_left > 0 && (
          <p>
            <button type="button" className="btn" onClick={() => { setResult(null); setAnswers({}); }}>
              Làm lại (còn {result.attempts_left} lượt)
            </button>
          </p>
        )}
      </>
    );
  }

  const answered = Object.keys(answers).length;

  return (
    <>
      <p className="muted"><Link href={`/lesson/${lessonId}`}>← Về bài học</Link></p>
      <h1>Luyện tập: {exam.lesson.title}</h1>
      <p className="muted">
        {exam.questions.length} câu · đã chọn {answered}/{exam.questions.length} · còn {exam.attempts_left} lượt
      </p>
      {error && <div className="alert alert-error">{error}</div>}

      {exam.questions.map((q, i) => (
        <fieldset className="q card" key={q.id}>
          <legend><b>{i + 1}.</b> {q.prompt}</legend>
          {q.options.map((opt, oi) => (
            <label className="opt" key={oi}>
              <input
                type="radio"
                name={`q_${q.id}`}
                value={LETTERS[oi]}
                checked={answers[q.id] === LETTERS[oi]}
                onChange={() => setAnswers((a) => ({ ...a, [q.id]: LETTERS[oi] }))}
              />{" "}
              <b>{LETTERS[oi]}.</b> {opt}
            </label>
          ))}
        </fieldset>
      ))}

      <button type="button" className="btn" onClick={submit}
              disabled={busy || answered < exam.questions.length}>
        {busy ? "Đang chấm…" : answered < exam.questions.length
          ? `Còn ${exam.questions.length - answered} câu chưa chọn`
          : "Nộp bài"}
      </button>
    </>
  );
}
