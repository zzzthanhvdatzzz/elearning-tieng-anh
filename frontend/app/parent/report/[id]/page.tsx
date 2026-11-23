import ReportView from "./ReportView";

export const instant = false;

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <ReportView studentId={id} />;
}
