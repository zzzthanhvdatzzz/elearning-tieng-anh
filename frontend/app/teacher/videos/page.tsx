"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import VideoBlock from "@/components/VideoBlock";

type Row = {
  id: number; code: string; title: string; skill: string;
  grade: number; unit: string;
  video_kind: "embed" | "file" | null; video_title: string;
};

const SKILL: Record<string, string> = {
  vocab: "Từ vựng", grammar: "Ngữ pháp", listening: "Nghe",
  reading: "Đọc", writing: "Viết", speaking: "Nói",
};

export default function TeacherVideosPage() {
  const router = useRouter();
  const [rows, setRows] = useState<Row[] | null>(null);
  const [grades, setGrades] = useState<number[]>([]);
  const [error, setError] = useState("");
  const [q, setQ] = useState("");
  const [grade, setGrade] = useState<number | "">("");
  const [onlyMissing, setOnlyMissing] = useState(false);
  const [selected, setSelected] = useState<number | null>(null);

  function load() {
    api<{ items: Row[]; grades: number[] }>("/api/teacher/lessons")
      .then((d) => {
        setRows(d.items);
        setGrades(d.grades);
        setSelected((cur) => cur ?? d.items[0]?.id ?? null);
      })
      .catch((e) => {
        if (e instanceof ApiError && (e.status === 401 || e.status === 403)) router.replace("/login");
        else setError("Không tải được danh sách bài học");
      });
  }
  useEffect(load, []);

  const shown = useMemo(() => {
    if (!rows) return null;
    const needle = q.trim().toLowerCase();
    return rows.filter((r) => {
      if (grade !== "" && r.grade !== grade) return false;
      if (onlyMissing && r.video_kind) return false;
      if (!needle) return true;
      return `${r.code} ${r.title} ${r.unit}`.toLowerCase().includes(needle);
    });
  }, [rows, q, grade, onlyMissing]);

  const current = rows?.find((r) => r.id === selected) ?? null;
  const withVideo = rows?.filter((r) => r.video_kind).length ?? 0;

  return (
    <div className="video-admin">
      <header className="video-admin-head">
        <div>
          <h1>Video bài giảng</h1>
          <p className="muted">
            {rows ? `${withVideo}/${rows.length} bài đã có video` : "Đang tải…"}
            {grades.length > 0 && ` · khối ${grades.join(", ")}`}
          </p>
        </div>
        <input className="video-search" value={q} onChange={(e) => setQ(e.target.value)}
               placeholder="Tìm theo mã bài, tên bài, Unit…" />
      </header>

      {error && <div className="alert alert-error">{error}</div>}

      <div className="video-admin-body">
        <aside className="video-list" aria-label="Danh sách bài học">
          <div className="video-filters">
            <select value={grade} onChange={(e) => setGrade(e.target.value === "" ? "" : Number(e.target.value))}>
              <option value="">Tất cả khối</option>
              {grades.map((g) => <option key={g} value={g}>Khối {g}</option>)}
            </select>
            <label className="video-check">
              <input type="checkbox" checked={onlyMissing}
                     onChange={(e) => setOnlyMissing(e.target.checked)} />
              Chưa có video
            </label>
          </div>

          {!shown && <p className="muted" style={{ padding: ".8rem" }}>Đang tải…</p>}
          {shown && shown.length === 0 && (
            <p className="muted" style={{ padding: ".8rem" }}>Không có bài nào khớp bộ lọc.</p>
          )}
          <ul className="video-items">
            {shown?.map((r) => (
              <li key={r.id}>
                <button type="button"
                        className={`video-item${r.id === selected ? " active" : ""}`}
                        onClick={() => setSelected(r.id)}>
                  <span className="video-item-dot" data-state={r.video_kind ? "yes" : "no"} aria-hidden />
                  <span className="video-item-text">
                    <b>{r.code}</b> {r.title}
                    <em>{r.unit} · {SKILL[r.skill] ?? r.skill}</em>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </aside>

        <main className="video-detail">
          {current ? (
            <>
              <div className="video-detail-head">
                <div>
                  <p className="video-kicker">Khối {current.grade} · {SKILL[current.skill] ?? current.skill}</p>
                  <h2>{current.code} — {current.title}</h2>
                  <p className="muted">{current.unit}</p>
                </div>
                <span className={`video-status${current.video_kind ? " on" : ""}`}>
                  {current.video_kind === "embed" ? "Link ngoài"
                    : current.video_kind === "file" ? "Đã tải lên" : "Chưa có video"}
                </span>
              </div>
              <VideoBlock lessonId={String(current.id)} onChanged={load} />
            </>
          ) : (
            <div className="card"><p className="muted">Chọn một bài ở danh sách bên trái.</p></div>
          )}
        </main>
      </div>
    </div>
  );
}
