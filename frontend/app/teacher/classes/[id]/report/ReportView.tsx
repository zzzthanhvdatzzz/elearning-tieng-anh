"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { API, api, ApiError } from "@/lib/api";

type Report = {
  klass: { id: number; name: string };
  students: number; class_avg: number | null;
  rows: { id: number; name: string; attempts: number; avg: number | null;
          minutes: number; needs_help: boolean }[];
};

export default function ReportView({ classId }: { classId: string }) {
  const router = useRouter();
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<Report>(`/api/teacher/classes/${classId}/report`)
      .then(setReport)
      .catch((err) => {
        if (err instanceof ApiError && (err.status === 401 || err.status === 403)) router.replace("/login");
        else setError(err instanceof ApiError ? err.message : "Lỗi tải báo cáo");
      });
  }, [classId, router]);

  if (error) return <div className="alert alert-error">{error}</div>;
  if (!report) return <p className="muted">Đang tải báo cáo…</p>;

  const help = report.rows.filter((r) => r.needs_help);

  return (
    <>
      <p className="muted"><Link href="/teacher/classes">← Về lớp của tôi</Link></p>
      <h1>Báo cáo lớp {report.klass.name}</h1>
      <p>{report.students} học sinh · điểm trung bình lớp{" "}
        <b>{report.class_avg ?? "—"}</b> / 10</p>

      {help.length > 0 && (
        <div className="card">
          <h2>Cần can thiệp ({help.length})</h2>
          <ul>
            {help.map((r) => (
              <li key={r.id}>{r.name} — {r.avg}/10 sau {r.attempts} bài</li>
            ))}
          </ul>
        </div>
      )}

      <div className="card">
        <h2>Bảng tổng hợp</h2>
        {report.rows.length === 0 ? <p className="muted">Lớp chưa có học sinh.</p> : (
          <table className="table">
            <thead><tr><th>Học sinh</th><th>Bài đã nộp</th><th>Điểm TB</th><th>Phút học</th></tr></thead>
            <tbody>
              {report.rows.map((r) => (
                <tr key={r.id}>
                  <td>{r.name}</td><td>{r.attempts}</td>
                  <td>{r.needs_help ? <span className="wrong">{r.avg}</span> : (r.avg ?? "—")}</td>
                  <td>{r.minutes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <p style={{ marginTop: "1rem" }}>
        <a className="btn ghost" href={`${API}/api/teacher/classes/${classId}/report.xlsx`}>
          ⬇ Tải bảng điểm (.xlsx)
        </a>
      </p>
    </>
  );
}
