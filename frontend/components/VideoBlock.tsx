"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { API, api, ApiError } from "@/lib/api";

type Progress = {
  watched_seconds: number; duration_seconds: number; position: number;
  percent: number; completed: boolean; needed_seconds: number;
};

type Info = {
  lesson: { id: number; title: string };
  kind: "embed" | "file" | null;
  embed_url: string | null;
  title: string;
  stream: string | null;
  can_manage: boolean;
  progress: Progress | null;
  rules?: { complete_ratio: number; heartbeat_seconds: number; seek_blocked: boolean };
};

const HEARTBEAT_MS = 10_000;

function mmss(sec: number) {
  const s = Math.max(0, Math.round(sec));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

export default function VideoBlock({ lessonId, onChanged }: { lessonId: string; onChanged?: () => void }) {
  const [info, setInfo] = useState<Info | null>(null);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [error, setError] = useState("");
  const [flash, setFlash] = useState("");
  const [warn, setWarn] = useState("");
  const [link, setLink] = useState("");
  const [title, setTitle] = useState("");
  const [busy, setBusy] = useState(false);
  const [openForm, setOpenForm] = useState(false);
  const [mode, setMode] = useState<"link" | "upload">("link");

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const maxAllowedRef = useRef(0);
  const lastSentRef = useRef(0);

  const load = useCallback(() => {
    api<Info>(`/api/lessons/${lessonId}/video`)
      .then((d) => {
        setInfo(d);
        setProgress(d.progress);
        maxAllowedRef.current = d.progress?.position ?? 0;
      })
      .catch(() => setInfo(null));
  }, [lessonId]);
  useEffect(load, [load]);

  useEffect(() => {
    if (!info || info.kind !== "file" || info.can_manage) return;
    const timer = setInterval(async () => {
      const v = videoRef.current;
      if (!v || v.paused || v.ended || !v.duration) return;
      const pos = Math.floor(v.currentTime);
      if (pos <= lastSentRef.current) return;
      lastSentRef.current = pos;
      try {
        const p = await api<Progress>(`/api/lessons/${lessonId}/video/heartbeat`, {
          method: "POST",
          body: JSON.stringify({ position: pos, duration: Math.round(v.duration) }),
        });
        setProgress(p);
        maxAllowedRef.current = p.position;
        if (p.completed) setFlash("Đã hoàn thành bài học.");
      } catch { /* nhịp sau gửi lại */ }
    }, HEARTBEAT_MS);
    return () => clearInterval(timer);
  }, [info, lessonId]);

  function onSeeking() {
    const v = videoRef.current;
    if (!v || info?.can_manage) return;
    const allowed = maxAllowedRef.current + 2;
    if (v.currentTime > allowed) {
      v.currentTime = maxAllowedRef.current;
      setWarn("Không tua được — xem tiếp từ chỗ đang dừng.");
      setTimeout(() => setWarn(""), 3000);
    }
  }

  function onPause() {
    const v = videoRef.current;
    if (!v || !v.duration || info?.can_manage) return;
    const pos = Math.floor(v.currentTime);
    if (pos <= lastSentRef.current) return;
    lastSentRef.current = pos;
    api<Progress>(`/api/lessons/${lessonId}/video/heartbeat`, {
      method: "POST", body: JSON.stringify({ position: pos, duration: Math.round(v.duration) }),
    }).then((p) => { setProgress(p); maxAllowedRef.current = p.position; }).catch(() => {});
  }

  async function saveLink(e: React.FormEvent) {
    e.preventDefault();
    setError(""); setFlash(""); setBusy(true);
    try {
      await api(`/api/teacher/lessons/${lessonId}/video`, {
        method: "POST", body: JSON.stringify({ url: link, title }),
      });
      setFlash("Đã gắn video.");
      onChanged?.();
      setLink(""); setTitle(""); setOpenForm(false);
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Không gắn được video");
    } finally { setBusy(false); }
  }

  async function upload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setError(""); setFlash(""); setBusy(true);
    const fd = new FormData();
    fd.append("file", file);
    fd.append("title", title || file.name);
    try {
      const res = await fetch(`${API}/api/teacher/lessons/${lessonId}/video/upload`, {
        method: "POST", body: fd, credentials: "include",
        headers: { "X-Requested-With": "fetch" },
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new ApiError(res.status, data?.detail ?? "Tải video thất bại");
      setFlash("Đã tải video lên.");
      onChanged?.();
      setTitle(""); setOpenForm(false);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Tải video thất bại");
    } finally { setBusy(false); e.target.value = ""; }
  }

  async function remove() {
    if (!confirm("Xoá video của bài này?")) return;
    setBusy(true);
    try {
      await api(`/api/teacher/lessons/${lessonId}/video`, { method: "DELETE" });
      setFlash("Đã xoá video.");
      onChanged?.();
      load();
    } catch { setError("Không xoá được video"); }
    finally { setBusy(false); }
  }

  if (!info) return null;

  const has = info.kind !== null;
  const manage = info.can_manage;

  return (
    <section className="video-card">
      <header className="video-head">
        <div>
          <p className="video-kicker">Bài giảng</p>
          <h2 className="video-title">{info.title || "Video bài giảng"}</h2>
        </div>
        {manage && (
          <div className="video-actions">
            <button type="button" className="btn ghost sm" onClick={() => setOpenForm((v) => !v)}>
              {has ? "Đổi video" : "Thêm video"}
            </button>
            {has && <button type="button" className="btn ghost sm" onClick={remove} disabled={busy}>Xoá</button>}
          </div>
        )}
      </header>

      {(flash || error || warn) && (
        <div className="video-notices">
          {flash && <div className="alert" style={{ background: "#e8f6ef", color: "#1b7f4b" }}>{flash}</div>}
          {error && <div className="alert alert-error">{error}</div>}
          {warn && <div className="alert" style={{ background: "#fff6e5", color: "#8a5a00" }}>{warn}</div>}
        </div>
      )}

      {info.kind === "embed" && info.embed_url && (
        <>
          <div className="video-frame">
            <iframe
              src={info.embed_url}
              title={info.title || "Video bài giảng"}
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
            />
          </div>
          {!manage && (
            <p className="video-note">
              Video nhúng từ YouTube/Drive — trình duyệt không cho chặn tua hay đo thời lượng chính xác,
              nên bài này không tính hoàn thành theo 80%.
            </p>
          )}
        </>
      )}

      {info.kind === "file" && info.stream && (
        <video
          ref={videoRef}
          className="video-player"
          controls
          preload="metadata"
          src={`${API}${info.stream}`}
          onSeeking={onSeeking}
          onPause={onPause}
          controlsList="nodownload"
          onContextMenu={(e) => { if (!manage) e.preventDefault(); }}
        >
          Trình duyệt không phát được video này.
        </video>
      )}

      {!has && !manage && <p className="video-note">Bài này chưa có video bài giảng.</p>}

      {!manage && progress && has && (
        <div className="video-progress">
          <div className="video-progress-track">
            <div className={`video-progress-fill${progress.completed ? " done" : ""}`}
                 style={{ width: `${progress.percent}%` }} />
          </div>
          <p className="video-progress-text">
            <b>{progress.percent}%</b>
            {progress.completed
              ? " · đã tính hoàn thành"
              : ` · còn ${mmss(progress.needed_seconds)} nữa để tính hoàn thành`}
            {progress.duration_seconds > 0 && ` · thời lượng ${mmss(progress.duration_seconds)}`}
          </p>
        </div>
      )}

      {manage && openForm && (
        <div className="video-form">
          <div className="video-tabs" role="tablist">
            <button type="button" role="tab" aria-selected={mode === "link"}
                    className={mode === "link" ? "tab active" : "tab"}
                    onClick={() => setMode("link")}>Dán link</button>
            <button type="button" role="tab" aria-selected={mode === "upload"}
                    className={mode === "upload" ? "tab active" : "tab"}
                    onClick={() => setMode("upload")}>Tải video lên</button>
          </div>

          <label className="video-label">Tên hiển thị (không bắt buộc)
            <input value={title} onChange={(e) => setTitle(e.target.value)}
                   placeholder="Unit 1 — Getting started" />
          </label>

          {mode === "link" ? (
            <form onSubmit={saveLink}>
              <label className="video-label">Link YouTube hoặc Google Drive
                <input value={link} onChange={(e) => setLink(e.target.value)}
                       placeholder="https://www.youtube.com/watch?v=..." />
              </label>
              <p className="video-hint">Hỗ trợ: youtube.com/watch, youtu.be, youtube.com/shorts, drive.google.com/file.</p>
              <button type="submit" disabled={busy || !link.trim()}>Gắn link</button>
            </form>
          ) : (
            <div>
              <label className="video-dropzone">
                <input type="file" accept="video/mp4,video/webm,video/quicktime"
                       onChange={upload} disabled={busy} />
                <span className="video-dropzone-text">
                  {busy ? "Đang tải lên…" : "Chọn tệp video (mp4 / webm / mov, tối đa 200 MB)"}
                </span>
              </label>
              <p className="video-hint">
                Video tải lên mới chặn được tua và tính hoàn thành khi xem ≥ 80%.
              </p>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
