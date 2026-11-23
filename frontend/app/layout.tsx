import type { Metadata } from "next";
import "./globals.css";
import Nav from "@/components/Nav";

export const metadata: Metadata = {
  title: "Học tiếng Anh trực tuyến — Nhóm 05",
  description: "Hệ thống học tiếng Anh cho học sinh THCS và THPT",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi">
      <body>
        <Nav />
        <main className="container">{children}</main>
        <footer className="foot">Nhóm 05 — Đồ án tích hợp hệ thống</footer>
      </body>
    </html>
  );
}
