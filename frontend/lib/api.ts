/**
 * lib/api.ts — mọi lời gọi API đi qua đây.
 *
 * Hai điều bắt buộc khi gọi FastAPI từ Next.js:
 * 1. `credentials: 'include'` — không có thì cookie phiên không được gửi/nhận.
 * 2. Header `X-Requested-With: fetch` — FastAPI dùng header này làm hàng rào CSRF cho API
 *    (trình duyệt không cho form HTML tự gắn header tuỳ biến, và header này buộc preflight
 *    nên origin lạ bị CORS chặn trước khi tới server).
 */
export const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8010";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "X-Requested-With": "fetch",
      ...(init.headers ?? {}),
    },
    cache: "no-store",
  });

  if (!res.ok) {
    let detail = `Lỗi ${res.status}`;
    try {
      const data = await res.json();
      // FastAPI trả `detail` là string (HTTPException) hoặc mảng (lỗi 422 validation)
      if (typeof data?.detail === "string") detail = data.detail;
      else if (Array.isArray(data?.detail)) {
        detail = data.detail.map((d: { loc?: string[]; msg?: string }) =>
          `${d.loc?.join(".") ?? ""}: ${d.msg ?? ""}`).join("; ");
      }
    } catch {
      /* body không phải JSON */
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

export type Me = { id: number; email: string; full_name: string; role: string; cefr: string | null; home: string };

export type UnitItem = {
  id: number; code: string; title: string; percent: number;
  lessons: { id: number; code: string; title: string; skill: string; percent: number }[];
};

export type UnitsResponse = {
  next: { id: number; title: string } | null;
  summary: { lessons_started: number; lessons_done: number; total_seconds: number };
  units: UnitItem[];
};

export type LessonDetail = {
  id: number; code: string; title: string; skill: string; unit: string;
  content: { objectives?: string[]; vocab?: { word: string; vi: string }[]; grammar?: string;
             reading?: string; minutes?: number };
  transcript: string | null; audio_url: string | null;
  percent: number; seconds: number; question_count: number;
};
