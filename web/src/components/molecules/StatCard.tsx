import { Badge } from "@/components/atoms/Badge";

interface StatCardProps {
  label: string;
  value: string;
  badge?: { text: string; variant: "default" | "success" | "warning" | "danger" };
}

/** Displays a label, a large number, and an optional badge. */
export function StatCard({ label, value, badge }: StatCardProps) {
  return (
    <div className="rounded-lg bg-[#1e3a2a] border border-[#2d4a38] px-4 py-3">
      <div className="text-xs text-[#8fa898] mb-1">{label}</div>
      <div className="text-xl font-semibold text-[#e8f0ec] tabular-nums">{value}</div>
      {badge && (
        <div className="mt-1">
          <Badge variant={badge.variant}>{badge.text}</Badge>
        </div>
      )}
    </div>
  );
}
