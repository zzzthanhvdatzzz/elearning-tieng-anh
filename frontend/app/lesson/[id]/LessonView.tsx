"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, ApiError, LessonDetail } from "@/lib/api";

export default function LessonView({ lessonId }: { lessonId: string }) {
  const router = useRouter();
  const [lesson, setLesson] = useState<LessonDetail | null>(null);
  const [error, setError] = useState("");
  const [percent, setPercent] = useState(0);
  const seconds = useRef(0);
  const sent = useRef(0);

  useEffect(() => {
    api<LessonDetail>(`/api/lessons/${lessonId}`)
      .then((l) => { setLesson(l); setPercent(l.percent); })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) router.replace("/login");
        else setError(err instanceof ApiError ? err.message : "Lỗi tải bài học");
      });
  }, [lessonId, router]);

  const flush = useCallback(async (payload: Record<string, unknown>, keepalive = false) => {
    try {
      const res = await api<{ percent: number; seconds: number }>(
        `/api/lessons/${lessonId}/progress`,
        { method: "POST", body: JSON.stringify(payload), keepalive },
      );
      setPercent(res.percent);
      sent.current = seconds.current;
    } catch { /* mất mạng thì lần sau gửi bù */ }
  }, [lessonId]);

  useEffect(() => {
    const timer = setInterval(() => { if (!document.hidden) seconds.current += 1; }, 1000);
    const push = setInterval(() => {
      if (seconds.current > sent.current) flush({ seconds: seconds.current - sent.current });
    }, 30000);
    const onHide = () => {
      if (seconds.current > sent.current) flush({ seconds: seconds.current - sent.current }, true);
    };
    window.addEventListener("pagehide", onHide);
    return () => {
      clearInterval(timer); clearInterval(push); window.removeEventListener("pagehide", onHide);
    };
  }, [flush]);

  async function markDone() {
    await flush({ completed: true });
    setPercent(100);
  }

  if (error) return <div className="alert alert-error">{error}</div>;
  if (!lesson) return <p className="muted">Đang tải bài học…</p>;

  const c = lesson.content ?? {};

  return (
    <>
      <p className="muted"><Link href="/units">← Lộ trình</Link> · {lesson.unit}</p>
      <h1>{lesson.title}</h1>

      {c.objectives && (
        <div className="card">
          <h2>Mục tiêu bài học</h2>
          <ul>{c.objectives.map((o) => <li key={o}>{o}</li>)}</ul>
        </div>
      )}

      {(lesson.audio_url || lesson.transcript) && (
        <div className="card">
          <h2>Phần nghe</h2>
          {lesson.audio_url
            ? <audio controls preload="none" src={lesson.audio_url} />
            : <p className="muted">Audio của bài này sẽ được nhóm Nội dung bổ sung.</p>}
          {lesson.transcript && (
            <details>
              <summary>Hiện transcript (nên nghe trước khi mở)</summary>
              <p className="explain" style={{ whiteSpace: "pre-line" }}>{lesson.transcript}</p>
            </details>
          )}
        </div>
      )}

      {c.vocab && (
        <div className="card">
          <h2>Từ vựng</h2>
          <table className="table">
            <thead><tr><th>Từ</th><th>Nghĩa</th></tr></thead>
            <tbody>
              {c.vocab.map((w) => <tr key={w.word}><td><b>{w.word}</b></td><td>{w.vi}</td></tr>)}
            </tbody>
          </table>
        </div>
      )}

      {c.grammar && <div className="card"><h2>Ngữ pháp</h2><p>{c.grammar}</p></div>}
      {c.reading && <div className="card"><h2>Bài đọc</h2><p style={{ whiteSpace: "pre-line" }}>{c.reading}</p></div>}

      <div className="card stats">
        <span>Tiến độ: <b>{percent}%</b></span>
        <Link className="btn" href={`/practice/${lesson.id}`} prefetch={false}>
          Luyện tập {lesson.question_count} câu
        </Link>
        {percent < 100 && <button type="button" className="btn" onClick={markDone}>Đánh dấu đã học xong</button>}
        {percent >= 100 && <span className="done">✓ Đã hoàn thành bài này</span>}
      </div>
    </>
  );
}
