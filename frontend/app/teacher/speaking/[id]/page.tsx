import GradeView from "./GradeView";

export const instant = false;

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <GradeView submissionId={id} />;
}
