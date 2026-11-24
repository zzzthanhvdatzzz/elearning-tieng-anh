import LessonView from "./LessonView";
import VideoBlock from "@/components/VideoBlock";

/**
 * Server Component: nhận `params` (Next 16 trả Promise) rồi truyền xuống client.
 * `instant = false` = route "blocking": cho phép đọc `params` lúc prerender thay vì bắt
 * buộc bọc <Suspense>. Đây là cấu hình route segment nên phải nằm ở Server Component,
 * không đặt được trong file "use client".
 */
export const instant = false;

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <>
      <VideoBlock lessonId={id} />
      <LessonView lessonId={id} />
    </>
  );
}
