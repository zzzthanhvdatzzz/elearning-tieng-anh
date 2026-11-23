"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { api, Me } from "@/lib/api";

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    api<Me>("/api/me")
      .then((me) => router.replace(me.role === "student" ? "/units" : "/login"))
      .catch(() => router.replace("/login"));
  }, [router]);

  return <p className="muted">Đang tải…</p>;
}
