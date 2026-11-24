"use client";

import { Fragment, useEffect, useState } from "react";
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
  const [openId, setOpenId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [onlyMissing, setOnlyMissing] = useState(false);

  function load() {
    api<{ items: Row[]; grades: number[] }>("/api/teacher/lessons")
      .then((d) => { setRows(d.items); setGrades(d.grades); })
      .catch((e) => {
        if (e instanceof ApiError && (e.status === 401 || e.status === 403)) router.replace("/login");
        else setError("Không tải được danh sách bài học");
      });
  }
  useEffect(load, []);

  const shown = rows ? (onlyMissing ? rows.filter((r) => !r.video_kind) : rows) : null;

  return (
    <>
      <div className="row-between">
        <h1>Video bài giảng</h1>
        <label className="muted" style={{ display: "flex", gap: ".4rem", alignItems: "center" }}>
          <input type="checkbox" checked={onlyMissing} style={{ width: "auto" }}
                 onChange={(e) => setOnlyMissing(e.target.checked)} />
          Chỉ bài chưa có video
        </label>
      </div>
      <p className="muted">
        {grades.length > 0 && <>Khối bạn dạy: {grades.join(", ")}. </>}
        Dán link YouTube/Drive hoặc tải video tự quay lên cho từng bài. Học sinh chỉ xem được
        video của khối mình học.
      </p>

      {error && <div className="alert alert-error">{error}</div>}
      {!shown && <p className="muted">Đang tải…</p>}
      {shown && shown.length === 0 && (
        <div className="card"><p className="muted">Không có bài học nào cần thêm video.</p></div>
      )}

      {shown && shown.length > 0 && (
        <table className="table">
          <thead>
            <tr><th>Bài</th><th>Khối</th><th>Kỹ năng</th><th>Video</th><th></th></tr>
          </thead>
          <tbody>
            {shown.map((r) => (
              <Fragment key={r.id}>
                <tr>
                  <td><b>{r.code}</b> — {r.title}<br /><span className="muted">{r.unit}</span></td>
                  <td>{r.grade}</td>
                  <td>{SKILL[r.skill] ?? r.skill}</td>
                  <td>
                    {r.video_kind === "embed" && <span className="done">Link ngoài</span>}
                    {r.video_kind === "file" && <span className="done">Đã tải lên</span>}
                    {!r.video_kind && <span className="muted">chưa có</span>}
                    {r.video_title ? <><br /><span className="muted">{r.video_title}</span></> : null}
                  </td>
                  <td>
                    <button type="button" className="btn ghost sm"
                            onClick={() => setOpenId(openId === r.id ? null : r.id)}>
                      {openId === r.id ? "Đóng" : r.video_kind ? "Sửa" : "+ Thêm video"}
                    </button>
                  </td>
                </tr>
                {openId === r.id && (
                  <tr>
                    <td colSpan={5} style={{ padding: 0, background: "transparent" }}>
                      <VideoBlock lessonId={String(r.id)} onChanged={load} />
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}
