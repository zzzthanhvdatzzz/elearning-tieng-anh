"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import WeeklyChart from "@/components/WeeklyChart";

type Report = {
  student: { id: number; name: string; cefr: string | null };
  minutes: number;
  skills: { skill: string; label: string; avg: number; count: number; weak: boolean }[];
  weakest: { label: string; avg: number } | null;
  weekly: { label: string; minutes: number }[];
  recent: { title: string; score: number | null; status: string; at: string }[];
};

export default function ReportView({ studentId }: { studentId: string }) {
  const router = useRouter();
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<Report>(`/api/reports/student/${studentId}`)
      .then(setReport)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) router.replace("/login");
        else setError(err instanceof ApiError ? err.message : "Lỗi tải báo cáo");
      });
  }, [studentId, router]);

  if (error) return <div className="alert alert-error">{error}</div>;
  if (!report) return <p className="muted">Đang tải báo cáo…</p>;

  return (
    <>
      <p className="muted"><Link href="/dashboard">← Về tổng quan</Link></p>
      <h1>Báo cáo của {report.student.name}</h1>

      <div className="grid-cards">
        <div className="stat-card"><div className="stat-value">{report.minutes}</div><div className="stat-label">phút đã học</div></div>
        <div className="stat-card"><div className="stat-value">{report.student.cefr ?? "—"}</div><div className="stat-label">trình độ CEFR</div></div>
        <div className="stat-card"><div className="stat-value">{report.skills.length}</div><div className="stat-label">kỹ năng đã có điểm</div></div>
      </div>

      <div className="card">
        <h2>Điểm theo kỹ năng</h2>
        {report.skills.length === 0 ? <p className="muted">Chưa có bài nào được chấm.</p> : (
          <table className="table">
            <thead><tr><th>Kỹ năng</th><th>Điểm trung bình</th><th>Số bài</th></tr></thead>
            <tbody>
              {report.skills.map((s) => (
                <tr key={s.skill}>
                  <td>{s.label}</td>
                  <td>{s.weak ? <span className="wrong">{s.avg}</span> : s.avg}</td>
                  <td>{s.count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {report.weakest && (
          <p className="explain">Kỹ năng yếu nhất: <b>{report.weakest.label}</b> ({report.weakest.avg}/10) — đây là căn cứ để gợi ý bài tiếp theo.</p>
        )}
      </div>

      <div className="card">
        <h2>Thời gian học 6 tuần gần đây</h2>
        <WeeklyChart data={report.weekly} />
      </div>

      <div className="card">
        <h2>Bài đã nộp gần đây</h2>
        {report.recent.length === 0 ? <p className="muted">Chưa nộp bài nào.</p> : (
          <table className="table">
            <thead><tr><th>Bài</th><th>Điểm</th><th>Trạng thái</th><th>Nộp lúc</th></tr></thead>
            <tbody>
              {report.recent.map((r, i) => (
                <tr key={i}>
                  <td>{r.title}</td>
                  <td>{r.score ?? "—"}</td>
                  <td>{r.status === "graded" ? "đã chấm" : "chờ chấm"}</td>
                  <td>{r.at}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
