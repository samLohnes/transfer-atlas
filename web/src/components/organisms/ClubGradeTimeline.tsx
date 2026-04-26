import { useMemo } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ClubReportCard } from "@/types/grade";

const CLUB_COLORS = ["#4ade80", "#38bdf8", "#c084fc"];

interface ClubGradeTimelineProps {
  clubs: ClubReportCard[];
}

interface ChartRow {
  transfer_window: string;
  /** Indexed by `club_${clubId}` so each club's series has a stable dataKey. */
  [seriesKey: string]: number | string | null;
}

/**
 * Recharts LineChart showing each selected club's average grade by transfer window.
 * Cross-window data is sparse: a club may not have transfers in every window the
 * other clubs do. We `connectNulls` so each line spans whatever windows it has.
 */
export function ClubGradeTimeline({ clubs }: ClubGradeTimelineProps) {
  const data = useMemo<ChartRow[]>(() => {
    if (clubs.length === 0) return [];
    const allWindows = new Set<string>();
    clubs.forEach((c) => c.timeline.forEach((t) => allWindows.add(t.transfer_window)));
    const sorted = Array.from(allWindows).sort(compareWindows);

    return sorted.map((win) => {
      const row: ChartRow = { transfer_window: win };
      clubs.forEach((c) => {
        const point = c.timeline.find((t) => t.transfer_window === win);
        row[`club_${c.club_id}`] = point ? point.average_grade : null;
        row[`count_${c.club_id}`] = point?.transfer_count ?? 0;
      });
      return row;
    });
  }, [clubs]);

  if (clubs.length === 0 || data.length === 0) {
    return null;
  }

  return (
    <div className="rounded-lg border border-white/[0.04] bg-white/[0.01] p-4">
      <h3 className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#6b8a78] mb-3">
        Average Grade by Transfer Window
      </h3>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={data} margin={{ top: 10, right: 16, left: 0, bottom: 24 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
          <XAxis
            dataKey="transfer_window"
            tick={{ fontSize: 10, fill: "#6b8a78" }}
            tickLine={false}
            axisLine={{ stroke: "rgba(255,255,255,0.04)" }}
            angle={-30}
            textAnchor="end"
            height={50}
            interval="preserveStartEnd"
          />
          <YAxis
            domain={[0, 100]}
            ticks={[0, 25, 40, 55, 70, 85, 100]}
            tick={{ fontSize: 10, fill: "#6b8a78" }}
            tickLine={false}
            axisLine={false}
            width={32}
          />
          {/* Threshold reference lines */}
          <ReferenceLine y={40} stroke="#f97316" strokeDasharray="3 3" strokeOpacity={0.25} />
          <ReferenceLine y={55} stroke="#fbbf24" strokeDasharray="3 3" strokeOpacity={0.25} />
          <ReferenceLine y={70} stroke="#2dd4bf" strokeDasharray="3 3" strokeOpacity={0.25} />
          <ReferenceLine y={85} stroke="#22c55e" strokeDasharray="3 3" strokeOpacity={0.25} />
          <Tooltip content={<TimelineTooltip clubs={clubs} />} />
          <Legend
            wrapperStyle={{ fontSize: 11, color: "#8fa898", paddingTop: 8 }}
            iconType="line"
          />
          {clubs.map((c, i) => (
            <Line
              key={c.club_id}
              dataKey={`club_${c.club_id}`}
              name={c.club_name}
              stroke={CLUB_COLORS[i % CLUB_COLORS.length]}
              strokeWidth={2}
              dot={{ r: 4, fill: CLUB_COLORS[i % CLUB_COLORS.length], strokeWidth: 0 }}
              activeDot={{ r: 6 }}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}


function TimelineTooltip({ active, payload, label, clubs }: any) { // eslint-disable-line @typescript-eslint/no-explicit-any
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-xl bg-[#0e1f16]/95 backdrop-blur-xl border border-white/[0.08] shadow-[0_8px_32px_rgba(0,0,0,0.4)] px-3.5 py-2.5 text-[12px]">
      <div className="font-semibold text-[#e8f0ec] mb-1.5">{label}</div>
      {payload.map((p: any) => { // eslint-disable-line @typescript-eslint/no-explicit-any
        const club = clubs.find((c: ClubReportCard) => `club_${c.club_id}` === p.dataKey);
        if (!club || p.value == null) return null;
        const point = club.timeline.find((t: any) => t.transfer_window === label); // eslint-disable-line @typescript-eslint/no-explicit-any
        return (
          <div key={p.dataKey} className="flex items-center gap-2 mb-0.5">
            <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: p.color }} />
            <span className="text-[#c5dace]">{p.name}</span>
            <span className="text-[#e8f0ec] tabular-nums ml-auto">
              {Math.round(Number(p.value))}
            </span>
            {point && (
              <span className="text-[#6b8a78] text-[11px]">({point.transfer_count})</span>
            )}
          </div>
        );
      })}
    </div>
  );
}


/** Order windows chronologically: parse "Summer 2020" / "Winter 2021" into a sortable tuple. */
function compareWindows(a: string, b: string): number {
  const re = /(Summer|Winter)\s+(\d{4})/;
  const ma = a.match(re);
  const mb = b.match(re);
  if (!ma || !mb) return a.localeCompare(b);
  const yearDiff = parseInt(ma[2], 10) - parseInt(mb[2], 10);
  if (yearDiff !== 0) return yearDiff;
  // Summer (0) before Winter (1) within the same year
  return (ma[1] === "Summer" ? 0 : 1) - (mb[1] === "Summer" ? 0 : 1);
}
