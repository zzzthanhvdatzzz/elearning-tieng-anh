"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";

type Report = {
  student: { id: number; name: string; cefr: string | null };
  minutes: number; submitted: number;
  skills: { skill: string; label: string; avg: number; count: number; weak: boolean }[];
  weakest: { label: string; avg: number } | null;
  weekly: { label: string; minutes: number }[];
};

export default function ReportView({ studentId }: { studentId: string }) {
  const router = useRouter();
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<Report>(`/api/parent/report/${studentId}`)
      .then(setReport)
      .catch((err) => {
        if (err instanceof ApiError && (err.status === 401 || err.status === 403)) router.replace("/parent");
        else setError(err instanceof ApiError ? err.message : "Lỗi tải báo cáo");
      });
  }, [studentId, router]);

  if (error) return <div className="alert alert-error">{error}</div>;
  if (!report) return <p className="muted">Đang tải báo cáo…</p>;

  return (
    <>
      <p className="muted"><Link href="/parent">← Về trang phụ huynh</Link></p>
      <h1>{report.student.name}</h1>

      <div className="card stats">
        <span><b>{report.minutes}</b> phút học</span>
        <span><b>{report.submitted}</b> bài đã nộp</span>
        <span><b>{report.student.cefr ?? "chưa xếp"}</b> trình độ</span>
      </div>

      <div className="card">
        <h2>Điểm theo kỹ năng</h2>
        {report.skills.length === 0 ? <p className="muted">Chưa có bài nào được chấm.</p> : (
          <table className="table">
            <thead><tr><th>Kỹ năng</th><th>Điểm trung bình</th></tr></thead>
            <tbody>
              {report.skills.map((s) => (
                <tr key={s.skill}>
                  <td>{s.label}</td>
                  <td>{s.weak ? <span className="wrong">{s.avg}</span> : s.avg}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {report.weakest && (
          <p className="explain">Con đang yếu nhất ở <b>{report.weakest.label}</b>. Nên nhắc con luyện thêm.</p>
        )}
      </div>
    </>
  );
}
