import { Badge } from "@/components/atoms/Badge";

interface StatCardProps {
  label: string;
  value: string;
  badge?: { text: string; variant: "default" | "success" | "warning" | "danger" };
}

/** Displays a label, a large number, and an optional badge. */
export function StatCard({ label, value, badge }: StatCardProps) {
  return (
    <div className="rounded-xl bg-white/[0.02] border border-white/[0.06] px-4 py-3">
      <div className="text-[10px] font-medium uppercase tracking-[0.1em] text-[#6b8a78] mb-1">{label}</div>
      <div className="text-xl font-semibold text-[#e8f0ec] font-data tabular-nums">{value}</div>
      {badge && (
        <div className="mt-1.5">
          <Badge variant={badge.variant}>{badge.text}</Badge>
        </div>
      )}
    </div>
  );
}
