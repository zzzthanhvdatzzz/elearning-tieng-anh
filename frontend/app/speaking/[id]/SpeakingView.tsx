"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, ApiError, API } from "@/lib/api";

type State = {
  lesson: { id: number; title: string }; prompt: string;
  attempts_left: number; max_attempts: number;
  last: { id: number; status: string; score: number | null } | null;
};

export default function SpeakingView({ lessonId }: { lessonId: string }) {
  const router = useRouter();
  const [state, setState] = useState<State | null>(null);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const [recording, setRecording] = useState(false);
  const [blob, setBlob] = useState<Blob | null>(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [secure, setSecure] = useState(true);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);

  useEffect(() => {
    api<State>(`/api/speaking/${lessonId}`)
      .then(setState)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) router.replace("/login");
        else setError(err instanceof ApiError ? err.message : "Lỗi tải đề");
      });
    setSecure(typeof navigator !== "undefined" && !!navigator.mediaDevices && !!window.MediaRecorder);
  }, [lessonId, router]);

  async function startRec() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const rec = new MediaRecorder(stream);
      chunks.current = [];
      rec.ondataavailable = (e) => chunks.current.push(e.data);
      rec.onstop = () => {
        const b = new Blob(chunks.current, { type: rec.mimeType || "audio/webm" });
        setBlob(b);
        setPreviewUrl(URL.createObjectURL(b));
        stream.getTracks().forEach((t) => t.stop());
      };
      rec.start();
      recorderRef.current = rec;
      setRecording(true);
      setStatus("Đang ghi…");
    } catch {
      setSecure(false);
      setStatus("");
    }
  }

  function stopRec() {
    recorderRef.current?.stop();
    setRecording(false);
    setStatus("Đã ghi xong — nghe lại rồi nộp.");
  }

  async function send(b: Blob) {
    const fd = new FormData();
    fd.append("file", b, "bai-noi.webm");
    setStatus("Đang nộp…");
    try {
      // FormData: KHÔNG đặt Content-Type thủ công để trình duyệt tự thêm boundary.
      const res = await fetch(`${API}/api/speaking/${lessonId}/upload`, {
        method: "POST", body: fd, credentials: "include",
        headers: { "X-Requested-With": "fetch" },
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({ detail: `Lỗi ${res.status}` }));
        throw new Error(d.detail ?? `Lỗi ${res.status}`);
      }
      setStatus("Đã nộp. Đang chờ giáo viên chấm.");
      setTimeout(() => router.refresh(), 800);
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Nộp thất bại");
    }
  }

  if (error) return <div className="alert alert-error">{error}</div>;
  if (!state) return <p className="muted">Đang tải…</p>;

  return (
    <>
      <p className="muted"><Link href={`/lesson/${lessonId}`}>← Về bài học</Link></p>
      <h1>Luyện nói: {state.lesson.title}</h1>
      <p className="muted">Còn {state.attempts_left}/{state.max_attempts} lượt</p>

      <div className="card">
        <h2>Đề bài</h2>
        <p>{state.prompt}</p>
      </div>

      <div className="card">
        <h2>Cách 1 — Ghi âm trên trình duyệt</h2>
        {!secure && (
          <div className="alert alert-error">
            Trình duyệt chặn micro vì trang không chạy HTTPS. Dùng cách 2 bên dưới.
          </div>
        )}
        <p>
          <button type="button" className="btn" onClick={startRec} disabled={!secure || recording}>
            ● Bắt đầu ghi
          </button>{" "}
          <button type="button" className="btn" onClick={stopRec} disabled={!recording}>■ Dừng</button>
        </p>
        {previewUrl && <audio controls src={previewUrl} />}
        {blob && <p><button type="button" className="btn" onClick={() => send(blob)}>Nộp bản ghi này</button></p>}
        <p className="muted">{status}</p>
      </div>

      <div className="card form">
        <h2>Cách 2 — Tải file ghi âm lên</h2>
        <p className="muted">Tối đa 10 MB (.webm, .ogg, .mp3, .m4a, .wav)</p>
        <input type="file" accept="audio/*"
               onChange={(e) => { const f = e.target.files?.[0]; if (f) send(f); }} />
      </div>

      {state.last && (
        <div className="card">
          <h2>Bài đã nộp</h2>
          <audio controls src={`${API}/audio/${state.last.id}`} />
          <p className="muted">
            {state.last.status === "graded" ? `Điểm: ${state.last.score}/10` : "Đang chờ giáo viên nghe và chấm."}
          </p>
        </div>
      )}
    </>
  );
}
