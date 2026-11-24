"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";

type Row = {
  id: number; at: string; actor: string; action: string;
  action_label: string; target: string; detail: string;
};

export default function AuditPage() {
  const router = useRouter();
  const [rows, setRows] = useState<Row[] | null>(null);
  const [actions, setActions] = useState<Record<string, string>>({});
  const [filter, setFilter] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api<{ items: Row[]; actions: Record<string, string> }>(`/api/admin/audit?action=${filter}`)
      .then((d) => { setRows(d.items); setActions(d.actions); })
      .catch((e) => {
        if (e instanceof ApiError && (e.status === 401 || e.status === 403)) router.replace("/login");
        else setError("Lỗi tải nhật ký");
      });
  }, [filter, router]);

  return (
    <>
      <h1>Nhật ký hoạt động</h1>
      <p className="muted">
        Ghi lại các thao tác nhạy cảm: khoá tài khoản, duyệt phụ huynh, chấm và mở lại bài.
        Không lưu nội dung bài làm của học sinh.
      </p>
      {error && <div className="alert alert-error">{error}</div>}

      <div className="card form">
        <label>Lọc theo loại
          <select value={filter} onChange={(e) => setFilter(e.target.value)}>
            <option value="">— tất cả —</option>
            {Object.entries(actions).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </label>
      </div>

      {!rows && <p className="muted">Đang tải…</p>}
      {rows && rows.length === 0 && <div className="card"><p className="muted">Chưa có ghi nhận nào.</p></div>}
      {rows && rows.length > 0 && (
        <table className="table">
          <thead><tr><th>Lúc</th><th>Người làm</th><th>Việc</th><th>Đối tượng</th><th>Chi tiết</th></tr></thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td>{r.at}</td><td>{r.actor || "—"}</td>
                <td>{r.action_label}</td><td>{r.target}</td><td>{r.detail}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}
