"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError, API } from "@/lib/api";

type Lesson = { id: number; code: string; title: string };
type Result = { added: number; errors: { row: number; reason: string }[] };

export default function AdminImportPage() {
  const router = useRouter();
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [lessonId, setLessonId] = useState("");
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api<{ items: Lesson[] }>("/api/admin/lessons")
      .then((d) => { setLessons(d.items); if (d.items[0]) setLessonId(String(d.items[0].id)); })
      .catch((err) => {
        if (err instanceof ApiError && (err.status === 401 || err.status === 403)) router.replace("/login");
        else setError("Lỗi tải danh sách bài học");
      });
  }, [router]);

  async function upload(file: File) {
    setBusy(true); setError(""); setResult(null);
    const fd = new FormData();
    fd.append("file", file);
    try {
      const res = await fetch(`${API}/api/admin/import-upload?lesson_id=${lessonId}`, {
        method: "POST", body: fd, credentials: "include",
        headers: { "X-Requested-With": "fetch" },
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? `Lỗi ${res.status}`);
      setResult(data as Result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Import thất bại");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <h1>Import câu hỏi từ Excel</h1>
      {error && <div className="alert alert-error">{error}</div>}

      <div className="card form">
        <label>Bài học nhận câu hỏi
          <select value={lessonId} onChange={(e) => setLessonId(e.target.value)}>
            {lessons.map((l) => <option key={l.id} value={l.id}>{l.code} — {l.title}</option>)}
          </select>
        </label>
        <label>File Excel (.xlsx, tối đa 5 MB)
          <input type="file" accept=".xlsx,.xlsm" disabled={busy}
                 onChange={(e) => { const f = e.target.files?.[0]; if (f) upload(f); }} />
        </label>
        <p className="muted">
          Cột bắt buộc: skill | prompt | option_a | option_b | option_c | option_d |
          correct_key | explanation. Dòng sai bị bỏ qua và liệt kê lý do.
        </p>
      </div>

      {result && (
        <div className="card">
          <h2>Kết quả</h2>
          <p><b>{result.added}</b> câu hợp lệ đã thêm ·{" "}
            <b className="wrong">{result.errors.length}</b> dòng lỗi</p>
          {result.errors.length > 0 && (
            <table className="table">
              <thead><tr><th>Dòng</th><th>Lý do</th></tr></thead>
              <tbody>
                {result.errors.map((e) => <tr key={e.row}><td>{e.row}</td><td>{e.reason}</td></tr>)}
              </tbody>
            </table>
          )}
        </div>
      )}
    </>
  );
}
