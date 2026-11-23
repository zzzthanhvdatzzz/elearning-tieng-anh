"use client";

/** Biểu đồ cột thuần CSS (không cần Chart.js) cho số phút học theo tuần. */
export default function WeeklyChart({
  data, unit = "phút",
}: {
  data: { label: string; minutes: number }[];
  unit?: string;
}) {
  if (!data || data.length === 0) return <p className="muted">Chưa có dữ liệu tuần.</p>;

  const max = Math.max(...data.map((d) => d.minutes), 1);
  const total = data.reduce((s, d) => s + d.minutes, 0);

  return (
    <>
      <div className="chart" role="img"
           aria-label={`Số ${unit} học theo tuần: ${data.map((d) => `${d.label} ${d.minutes}`).join(", ")}`}>
        {data.map((d) => (
          <div className="chart-col" key={d.label} title={`${d.label}: ${d.minutes} ${unit}`}>
            <div className="chart-bar" style={{ height: `${Math.max(4, (d.minutes / max) * 120)}px` }} />
            <div className="chart-label">{d.minutes}</div>
          </div>
        ))}
      </div>
      <p className="muted" style={{ display: "flex", justifyContent: "space-between", margin: 0 }}>
        <span>{data[0]?.label}</span>
        <span>tổng {total} {unit}</span>
        <span>{data[data.length - 1]?.label}</span>
      </p>
    </>
  );
}
