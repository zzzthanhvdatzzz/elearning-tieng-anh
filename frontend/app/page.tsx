"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, Me } from "@/lib/api";

export default function Home() {
  const router = useRouter();

  // Render trang giới thiệu ngay trong HTML; nếu đã có phiên thì mới chuyển hướng.
  useEffect(() => {
    api<Me>("/api/me")
      .then((me) => router.replace(me.home))
      .catch(() => { /* chưa đăng nhập → giữ trang giới thiệu */ });
  }, [router]);

  return (
    <>
      <section className="meadow">
        <h1>Học tiếng Anh <em>qua bốn kỹ năng.</em></h1>
        <p>
          Hệ thống luyện nghe – nói – đọc – viết cho học sinh THCS và THPT. Bài tập chấm ngay,
          giáo viên chấm bài viết theo rubric, phụ huynh nhận báo cáo tuần.
        </p>
        <p className="cta">
          <Link className="btn" href="/login">Đăng nhập</Link>
          <Link href="/register">Đăng ký bằng mã lớp →</Link>
        </p>
      </section>

      <div className="steps">
        <div className="card step">
          <span className="step-no">1</span>
          <strong>Kiểm tra đầu vào</strong>
          <p className="muted">25 câu trắc nghiệm + một bài viết. Hệ thống đề xuất trình độ A1–B2, giáo viên xác nhận.</p>
        </div>
        <div className="card step">
          <span className="step-no">2</span>
          <strong>Học và luyện mỗi ngày</strong>
          <p className="muted">Lộ trình theo Unit của sách. Trắc nghiệm chấm trong vài giây, bài viết và bài nói do giáo viên chấm.</p>
        </div>
        <div className="card step">
          <span className="step-no">3</span>
          <strong>Nhìn thấy kết quả</strong>
          <p className="muted">Học sinh thấy kỹ năng nào còn yếu; giáo viên thấy em nào cần giúp; phụ huynh nhận báo cáo tuần.</p>
        </div>
      </div>

      <div className="card">
        <h2>Dành cho ai</h2>
        <ul className="lesson-list">
          <li><b>Học sinh</b> — học bài có audio, luyện tập chấm ngay, ghi âm bài nói, xem điểm và phản hồi.</li>
          <li><b>Giáo viên</b> — tạo lớp, giao bài có hạn, chấm bài viết theo 4 tiêu chí, xem báo cáo lớp.</li>
          <li><b>Phụ huynh</b> — liên kết với tài khoản của con (giáo viên duyệt), xem báo cáo tuần.</li>
          <li><b>Quản trị</b> — quản lý tài khoản, ngân hàng câu hỏi, import đề từ Excel.</li>
        </ul>
      </div>

      <div className="card limits">
        <h2>Giới hạn của bản này</h2>
        <p className="muted">
          Đây là sản phẩm bài tập lớn của Nhóm 05: nội dung mẫu gồm 4 Unit, chưa có ứng dụng di động,
          chưa chấm nói tự động bằng AI, và audio bài nghe đang được nhóm Nội dung bổ sung.
        </p>
      </div>

      <p className="muted" style={{ textAlign: "center", marginTop: "1.5rem" }}>
        Phụ huynh chưa có tài khoản? <Link href="/login">Đăng nhập</Link> rồi dùng mục liên kết,
        hoặc xem hướng dẫn trong báo cáo tuần.
      </p>
    </>
  );
}
