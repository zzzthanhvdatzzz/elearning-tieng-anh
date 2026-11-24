"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, ApiError, Me } from "@/lib/api";

type Any = Record<string, any>;

const ROLE_LABEL: Record<string, string> = {
  student: "Học sinh", teacher: "Giáo viên", parent: "Phụ huynh", admin: "Quản trị",
};

export default function DashboardPage() {
  const router = useRouter();
  const [data, setData] = useState<Any | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<Me>("/api/me").catch(() => router.replace("/login"));
    api<Any>("/api/dashboard")
      .then(setData)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) router.replace("/login");
        else setError(err instanceof ApiError ? err.message : "Lỗi tải tổng quan");
      });
  }, [router]);

  if (error) return <div className="alert alert-error">{error}</div>;
  if (!data) return <p className="muted">Đang tải…</p>;

  return (
    <>
      <header className="dashboard-welcome">
        <div className="dashboard-greeting">
        <p className="dashboard-label">Góc học tập EnglishHub</p>
        <h1>Xin chào, {data.name}</h1>
        <p className="muted">
          {ROLE_LABEL[data.role] ?? data.role}
          {data.cefr ? ` · trình độ ${data.cefr}` : ""}
          {data.klass ? ` · lớp ${data.klass.name}` : ""}
        </p>
        </div>
      </header>

      {data.role === "student" && <StudentDash d={data} />}
      {data.role === "teacher" && <TeacherDash d={data} />}
      {data.role === "parent" && <ParentDash d={data} />}
      {data.role === "admin" && <AdminDash d={data} />}
    </>
  );
}

function Stat({ value, label }: { value: React.ReactNode; label: string }) {
  return (
    <div className="stat-card">
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  );
}

function StudentDash({ d }: { d: Any }) {
  return (
    <>
      <div className="grid-cards">
        <Stat value={d.summary.lessons_done} label="bài đã hoàn thành" />
        <Stat value={Math.round(d.summary.total_seconds / 60)} label="phút đã học" />
        <Stat value={d.todo_count} label="bài cần làm" />
        {d.videos && d.videos.videos_total > 0 && (
          <Stat value={`${d.videos.videos_completed}/${d.videos.videos_total}`}
                label="video đã xem xong" />
        )}
      </div>

      {d.videos && d.videos.videos_total > 0 && (
        <div className="card">
          <div className="row-between">
            <h2>Video bài giảng</h2>
            <Link className="link" href="/units">Xem tất cả bài →</Link>
          </div>
          <div className="video-progress-track" style={{ marginBottom: ".6rem" }}>
            <div className={`video-progress-fill${d.videos.percent === 100 ? " done" : ""}`}
                 style={{ width: `${d.videos.percent}%` }} />
          </div>
          <p className="video-progress-text">
            Đã xem xong <b>{d.videos.videos_completed}/{d.videos.videos_total}</b> video bài giảng
            {d.videos.watched_seconds > 0 && ` · tổng ${Math.round(d.videos.watched_seconds / 60)} phút`}
          </p>
          {d.videos.items.some((v: { completed: boolean }) => !v.completed) && (
            <ul className="lesson-list">
              {d.videos.items
                .filter((v: { completed: boolean }) => !v.completed)
                .slice(0, 3)
                .map((v: { lesson_id: number; title: string; percent: number }) => (
                  <li key={v.lesson_id}>
                    <span>{v.title}</span>
                    <span className="muted">đã xem {v.percent}%</span>
                    <Link className="link" href={`/lesson/${v.lesson_id}`}>Xem tiếp →</Link>
                  </li>
                ))}
            </ul>
          )}
        </div>
      )}

      {d.next ? (
        <div className="card nextup">
          <p className="muted">Bài tiếp theo · {d.next.unit}</p>
          <p><strong>{d.next.title}</strong></p>
          <Link className="btn" href={`/lesson/${d.next.id}`}>Học ngay →</Link>
        </div>
      ) : (
        <div className="card">
          <p>Bạn đã hoàn thành toàn bộ bài học hiện có.</p>
          <Link className="btn" href="/units">Xem lộ trình</Link>
        </div>
      )}

      <div className="card">
        <h2>Việc cần làm</h2>
        {d.todo.length === 0 ? (
          <p className="muted">Không có bài nào đang chờ. <Link href="/assignments">Xem tất cả</Link></p>
        ) : (
          <ul className="lesson-list">
            {d.todo.map((t: Any) => (
              <li key={t.id}>
                {t.title}
                {t.deadline && <span className="muted"> · hạn {new Date(t.deadline).toLocaleString("vi-VN")}</span>}
                <span className="skill">còn {t.attempts_left} lượt</span>
                {t.lesson_id && (
                  <Link href={t.kind === "writing" ? `/writing/${t.lesson_id}` : `/practice/${t.lesson_id}`}>
                    {" "}Làm bài →
                  </Link>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="card">
        <h2>Bài đã nộp gần đây</h2>
        {d.recent.length === 0 ? <p className="muted">Chưa nộp bài nào.</p> : (
          <table className="table">
            <thead><tr><th>Bài</th><th>Điểm</th><th>Trạng thái</th><th>Lúc</th></tr></thead>
            <tbody>
              {d.recent.map((r: Any) => (
                <tr key={r.id}>
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

      <div className="card">
        <h2>Lộ trình</h2>
        <ul className="lesson-list">
          {d.units.map((u: Any) => (
            <li key={u.id}>
              <Link href="/units">{u.title}</Link>
              <span className="muted"> · {u.lessons} bài · hoàn thành {u.percent}%</span>
            </li>
          ))}
        </ul>
      </div>
    </>
  );
}

function TeacherDash({ d }: { d: Any }) {
  return (
    <>
      <div className="grid-cards">
        <Stat value={d.classes.length} label="lớp phụ trách" />
        <Stat value={d.students} label="học sinh" />
        <Stat value={d.pending_grading} label="bài chờ chấm" />
        <Stat value={d.parent_requests} label="yêu cầu phụ huynh" />
      </div>

      <div className="grid-actions dashboard-actions">
        <Link className="card action" href="/teacher/classes">
          <strong>Lớp &amp; giao bài</strong>
          <span className="muted">Tạo lớp, thêm học sinh, giao bài có hạn</span>
        </Link>
        <Link className="card action" href="/teacher/writing">
          <strong>Chấm bài ({d.pending_grading})</strong>
          <span className="muted">Chấm rubric 4 tiêu chí, trả bài</span>
        </Link>
        <Link className="card action" href="/teacher/parents">
          <strong>Duyệt phụ huynh ({d.parent_requests})</strong>
          <span className="muted">Xác nhận liên kết trước khi phụ huynh xem báo cáo</span>
        </Link>
      </div>

      <div className="card">
        <h2>Lớp của tôi</h2>
        {d.classes.length === 0 ? <p className="muted">Chưa có lớp. <Link href="/teacher/classes">Tạo lớp</Link></p> : (
          <table className="table">
            <thead><tr><th>Lớp</th><th>Khối</th><th>Mã tham gia</th><th></th></tr></thead>
            <tbody>
              {d.classes.map((c: Any) => (
                <tr key={c.id}>
                  <td>{c.name}</td><td>{c.grade}</td><td><code>{c.join_code}</code></td>
                  <td><Link href="/teacher/classes">Quản lý →</Link></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}

function ParentDash({ d }: { d: Any }) {
  const approved = d.children.filter((c: Any) => c.status === "approved");
  return (
    <>
      <div className="card">
        <h2>Liên kết với con</h2>
        {d.children.length === 0 ? (
          <p className="muted">Chưa có liên kết. <Link href="/parent">Gửi yêu cầu liên kết</Link></p>
        ) : (
          <ul className="lesson-list">
            {d.children.map((c: Any) => (
              <li key={c.id}>
                {c.status === "approved" ? <Link href={`/parent/report/${c.id}`}>{c.name}</Link> : c.name}
                <span className="skill">{c.status === "approved" ? "đã duyệt" : "chờ duyệt"}</span>
                {c.status === "approved" && <span className="muted"> · {c.minutes} phút học</span>}
              </li>
            ))}
          </ul>
        )}
        {approved.length > 0 && <p><Link className="btn" href={`/parent/report/${approved[0].id}`}>Xem báo cáo →</Link></p>}
      </div>
      <div className="card">
        <p className="muted"><Link href="/parent">Quản lý liên kết</Link></p>
      </div>
    </>
  );
}

function AdminDash({ d }: { d: Any }) {
  return (
    <>
      <div className="grid-cards">
        <Stat value={d.users} label="tài khoản" />
        <Stat value={d.students} label="học sinh" />
        <Stat value={d.teachers} label="giáo viên" />
        <Stat value={d.classes} label="lớp" />
        <Stat value={d.submissions} label="bài nộp" />
      </div>
      <div className="grid-actions">
        <Link className="card action" href="/admin/users">
          <strong>Quản lý tài khoản</strong>
          <span className="muted">Tạo, khoá/mở, đặt lại mật khẩu</span>
        </Link>
        <Link className="card action" href="/admin/import">
          <strong>Import câu hỏi</strong>
          <span className="muted">Nạp đề từ Excel, báo lỗi từng dòng</span>
        </Link>
      </div>
    </>
  );
}
