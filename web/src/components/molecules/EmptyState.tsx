import { SearchX } from "lucide-react";
import type { LucideIcon } from "lucide-react";

interface EmptyStateProps {
  message: string;
  icon?: LucideIcon;
}

/** Displays a message when no data matches the current filters. */
export function EmptyState({ message, icon: Icon = SearchX }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-[#8fa898]">
      <Icon className="h-12 w-12 mb-4 opacity-40" />
      <p className="text-sm">{message}</p>
    </div>
  );
}
