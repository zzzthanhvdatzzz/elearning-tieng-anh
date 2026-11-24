"use client";

import { useEffect, useState } from "react";
import { API, api, ApiError } from "@/lib/api";

type Info = {
  lesson: { id: number; title: string };
  kind: "embed" | "file" | null;
  embed_url: string | null;
  title: string;
  stream: string | null;
  can_manage: boolean;
};

export default function VideoBlock({ lessonId, onChanged }: { lessonId: string; onChanged?: () => void }) {
  const [info, setInfo] = useState<Info | null>(null);
  const [error, setError] = useState("");
  const [flash, setFlash] = useState("");
  const [link, setLink] = useState("");
  const [title, setTitle] = useState("");
  const [busy, setBusy] = useState(false);
  const [openForm, setOpenForm] = useState(false);

  function load() {
    api<Info>(`/api/lessons/${lessonId}/video`)
      .then(setInfo)
      .catch(() => setInfo(null));   // chưa có video hoặc không có quyền: ẩn, không báo lỗi
  }
  useEffect(load, [lessonId]);

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
        headers: { "X-Requested-With": "fetch" },     // KHÔNG tự đặt Content-Type: để trình duyệt tự sinh boundary
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
    } catch {
      setError("Không xoá được video");
    } finally { setBusy(false); }
  }

  if (!info) return null;

  const has = info.kind !== null;

  return (
    <div className="card">
      <div className="row-between">
        <h2>Video bài giảng</h2>
        {info.can_manage && (
          <span style={{ display: "flex", gap: ".5rem" }}>
            <button type="button" className="btn ghost sm" onClick={() => setOpenForm((v) => !v)}>
              {has ? "Đổi video" : "+ Thêm video"}
            </button>
            {has && (
              <button type="button" className="btn ghost sm" onClick={remove} disabled={busy}>
                Xoá
              </button>
            )}
          </span>
        )}
      </div>

      {flash && <div className="alert" style={{ background: "#e8f6ef", color: "#1b7f4b" }}>{flash}</div>}
      {error && <div className="alert alert-error">{error}</div>}

      {has && info.title && <p className="muted">{info.title}</p>}

      {info.kind === "embed" && info.embed_url && (
        <div style={{ position: "relative", paddingTop: "56.25%", marginTop: ".5rem" }}>
          <iframe
            src={info.embed_url}
            title={info.title || "Video bài giảng"}
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
            style={{ position: "absolute", inset: 0, width: "100%", height: "100%", border: 0, borderRadius: 12 }}
          />
        </div>
      )}

      {info.kind === "file" && info.stream && (
        <video controls preload="metadata" src={`${API}${info.stream}`}
               style={{ width: "100%", borderRadius: 12, marginTop: ".5rem", background: "#000" }}>
          Trình duyệt không phát được video này.
        </video>
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
            Hoặc tải video tự quay lên (mp4/webm/mov, tối đa 200 MB):
          </p>
          <input type="file" accept="video/mp4,video/webm,video/quicktime"
                 onChange={upload} disabled={busy} style={{ marginTop: ".3rem" }} />
        </form>
      )}
    </div>
  );
}
