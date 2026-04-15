import { SearchX } from "lucide-react";
import type { LucideIcon } from "lucide-react";

interface EmptyStateProps {
  message: string;
  icon?: LucideIcon;
}

/** Displays a message when no data matches the current filters. */
export function EmptyState({ message, icon: Icon = SearchX }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-[#4a6555]">
      <div className="w-12 h-12 rounded-2xl bg-white/[0.03] border border-white/[0.06] flex items-center justify-center mb-4">
        <Icon className="h-5 w-5 opacity-50" />
      </div>
      <p className="text-[13px] text-center max-w-[280px] leading-relaxed">{message}</p>
    </div>
  );
}
