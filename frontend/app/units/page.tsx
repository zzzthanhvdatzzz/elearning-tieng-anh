"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, ApiError, Me, UnitsResponse } from "@/lib/api";

export default function UnitsPage() {
  const router = useRouter();
  const [data, setData] = useState<UnitsResponse | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<UnitsResponse>("/api/units")
      .then(setData)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) router.replace("/login");
        else setError(err instanceof ApiError ? err.message : "Lỗi tải lộ trình");
      });
  }, [router]);

  if (error) return <div className="alert alert-error">{error}</div>;
  if (!data) return <p className="muted">Đang tải lộ trình…</p>;

  return (
    <>
      <h1>Lộ trình học</h1>
      <div className="card stats">
        <span><b>{data.summary.lessons_done}</b> bài hoàn thành</span>
        <span><b>{data.summary.lessons_started}</b> bài đã học</span>
        <span><b>{Math.round(data.summary.total_seconds / 60)}</b> phút học</span>
      </div>

      {data.next && (
        <div className="card nextup">
          <p className="muted">Bài tiếp theo</p>
          <p><strong>{data.next.title}</strong></p>
          <p><Link className="btn" href={`/lesson/${data.next.id}`}>Học tiếp →</Link></p>
        </div>
      )}

      {data.units.map((unit) => (
        <section className="card" key={unit.id}>
          <h2>{unit.title}</h2>
          <p className="muted">Unit {unit.code} · {unit.lessons.length} bài · hoàn thành {unit.percent}%</p>
          <ol className="lesson-list">
            {unit.lessons.map((l) => (
              <li key={l.id}>
                <Link href={`/lesson/${l.id}`}>{l.title}</Link>
                <span className="skill">{l.skill}</span>
                {l.percent >= 100 ? <span className="done">✓ đã học</span>
                  : l.percent > 0 ? <span className="muted"> {l.percent}%</span> : null}
              </li>
            ))}
          </ol>
        </section>
      ))}

      {data.units.length === 0 && (
        <div className="alert alert-error">Bạn chưa được ghi danh vào lớp nào, nên chưa có lộ trình.</div>
      )}
    </>
  );
}
