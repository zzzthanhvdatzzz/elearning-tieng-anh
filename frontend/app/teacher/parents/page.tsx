"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";

type Klass = { id: number; name: string; grade: number; join_code: string; students: number };
type Row = { id: number; student: string; parent: string; klass: string };

export default function TeacherParentsPage() {
  const router = useRouter();
  const [rows, setRows] = useState<Row[] | null>(null);
  const [error, setError] = useState("");

  async function load() {
    try {
      const d = await api<{ items: Row[] }>("/api/teacher/parent-requests");
      setRows(d.items);
    } catch (err) {
      if (err instanceof ApiError && (err.status === 401 || err.status === 403)) router.replace("/login");
      else setError("Lỗi tải danh sách");
    }
  }

  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function decide(id: number, approve: boolean) {
    await api(`/api/teacher/parent-requests/${id}`, {
      method: "POST", body: JSON.stringify({ approve }),
    });
    load();
  }

  return (
    <>
      <h1>Yêu cầu liên kết phụ huynh</h1>
      {error && <div className="alert alert-error">{error}</div>}
      {!rows && <p className="muted">Đang tải…</p>}
      {rows && rows.length === 0 && <div className="card"><p>Không có yêu cầu nào đang chờ.</p></div>}
      {rows && rows.length > 0 && (
        <table className="table">
          <thead><tr><th>Học sinh</th><th>Lớp</th><th>Phụ huynh</th><th></th></tr></thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td>{r.student}</td><td>{r.klass}</td><td>{r.parent}</td>
                <td>
                  <button type="button" className="link" onClick={() => decide(r.id, true)}>Duyệt</button>{" · "}
                  <button type="button" className="link" onClick={() => decide(r.id, false)}>Từ chối</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}
