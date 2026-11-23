import SpeakingView from "./SpeakingView";

export const instant = false;

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <SpeakingView lessonId={id} />;
}
