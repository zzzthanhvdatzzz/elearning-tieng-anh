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

const HEARTBEAT_MS = 10_000;   // khớp với server: mỗi nhịp cộng tối đa 20 giây

export default function VideoBlock({ lessonId, onChanged }: { lessonId: string; onChanged?: () => void }) {
  const [info, setInfo] = useState<Info | null>(null);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [error, setError] = useState("");
  const [flash, setFlash] = useState("");
  const [link, setLink] = useState("");
  const [title, setTitle] = useState("");
  const [busy, setBusy] = useState(false);
  const [openForm, setOpenForm] = useState(false);
  const [warn, setWarn] = useState("");

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const maxAllowedRef = useRef(0);      // vị trí xa nhất được phép tua tới
  const lastSentRef = useRef(0);        // vị trí đã gửi gần nhất

  const load = useCallback(() => {
    api<Info>(`/api/lessons/${lessonId}/video`)
      .then((d) => {
        setInfo(d);
        setProgress(d.progress);
        maxAllowedRef.current = d.progress?.position ?? 0;
      })
      .catch(() => setInfo(null));   // chưa có video hoặc không có quyền: ẩn
  }, [lessonId]);
  useEffect(load, [load]);

  // Nhịp tim: chỉ gửi khi đang phát, để server cộng đúng phần thực xem
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
        if (p.completed) setFlash("Đã hoàn thành bài học (xem ≥ 80%).");
      } catch {
        /* mất mạng tạm thời: nhịp sau gửi lại */
      }
    }, HEARTBEAT_MS);
    return () => clearInterval(timer);
  }, [info, lessonId]);

  // Chặn tua tới: kéo thanh tới vượt vị trí đã xem thì kéo về chỗ cũ
  function onSeeking() {
    const v = videoRef.current;
    if (!v || info?.can_manage) return;
    const allowed = maxAllowedRef.current + 2;   // +2s dung sai cho bộ đệm
    if (v.currentTime > allowed) {
      v.currentTime = maxAllowedRef.current;
      setWarn("Không tua được: bạn phải xem tiếp từ chỗ đang dừng.");
      setTimeout(() => setWarn(""), 3000);
    }
  }

  // Ghi nhận khi dừng/thoát giữa chừng
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
      setFlash("Đã gắn video từ link.");
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
  const isStudent = !info.can_manage;

  return (
    <div className="card">
      <div className="row-between">
        <h2>Video bài giảng</h2>
        {info.can_manage && (
          <span style={{ display: "flex", gap: ".5rem" }}>
            <button type="button" className="btn ghost sm" onClick={() => setOpenForm((v) => !v)}>
              {has ? "Đổi video" : "+ Thêm video"}
            </button>
            {has && <button type="button" className="btn ghost sm" onClick={remove} disabled={busy}>Xoá</button>}
          </span>
        )}
      </div>

      {flash && <div className="alert" style={{ background: "#e8f6ef", color: "#1b7f4b" }}>{flash}</div>}
      {error && <div className="alert alert-error">{error}</div>}
      {warn && <div className="alert" style={{ background: "#fff6e5", color: "#8a5a00" }}>{warn}</div>}

      {has && info.title && <p className="muted">{info.title}</p>}

      {info.kind === "embed" && info.embed_url && (
        <>
          <div style={{ position: "relative", paddingTop: "56.25%", marginTop: ".5rem" }}>
            <iframe
              src={info.embed_url}
              title={info.title || "Video bài giảng"}
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
              style={{ position: "absolute", inset: 0, width: "100%", height: "100%", border: 0, borderRadius: 12 }}
            />
          </div>
          {isStudent && (
            <p className="muted" style={{ marginTop: ".5rem" }}>
              Video nhúng từ YouTube/Drive: trình duyệt không cho hệ thống chặn tua hay đo thời lượng
              chính xác. Muốn tính hoàn thành theo 80%, giáo viên cần tải video lên hệ thống.
            </p>
          )}
        </>
      )}

      {info.kind === "file" && info.stream && (
        <video
          ref={videoRef}
          controls
          preload="metadata"
          src={`${API}${info.stream}`}
          onSeeking={onSeeking}
          onPause={onPause}
          controlsList="nodownload"
          onContextMenu={(e) => { if (isStudent) e.preventDefault(); }}
          style={{ width: "100%", borderRadius: 12, marginTop: ".5rem", background: "#000" }}
        >
          Trình duyệt không phát được video này.
        </video>
      )}

      {isStudent && progress && has && (
        <div style={{ marginTop: ".7rem" }}>
          <div style={{ height: 8, background: "#e3e8ef", borderRadius: 999, overflow: "hidden" }}>
            <div style={{
              width: `${progress.percent}%`, height: "100%",
              background: progress.completed ? "#079455" : "#35664b", transition: "width .3s",
            }} />
          </div>
          <p className="muted" style={{ marginTop: ".4rem" }}>
            Đã xem <b>{progress.percent}%</b>
            {progress.completed
              ? " — đã tính hoàn thành (≥ 80%)."
              : ` — cần thêm ${Math.max(0, progress.needed_seconds)} giây nữa để tính hoàn thành.`}
            {progress.duration_seconds > 0 && ` Thời lượng ${Math.floor(progress.duration_seconds / 60)} phút ${progress.duration_seconds % 60} giây.`}
          </p>
        </div>
      )}

      {!has && <p className="muted">Bài này chưa có video. Giáo viên có thể dán link YouTube hoặc tải video tự quay lên.</p>}

      {info.can_manage && openForm && (
        <form className="form" onSubmit={saveLink} style={{ marginTop: "1rem" }}>
          <label>Tên video (không bắt buộc)
            <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Unit 1 — Getting started" />
          </label>
          <label>Link YouTube hoặc Google Drive
            <input value={link} onChange={(e) => setLink(e.target.value)}
                   placeholder="https://www.youtube.com/watch?v=..." />
          </label>
          <button type="submit" disabled={busy || !link.trim()}>Gắn link</button>

          <p className="muted" style={{ marginTop: "1rem" }}>
            Hoặc tải video tự quay lên (mp4/webm/mov, tối đa 200 MB). Video tải lên mới chặn được tua
            và tính hoàn thành theo 80%:
          </p>
          <input type="file" accept="video/mp4,video/webm,video/quicktime"
                 onChange={upload} disabled={busy} style={{ marginTop: ".3rem" }} />
        </form>
      )}
    </div>
  );
}
