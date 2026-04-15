import { AlertTriangle } from "lucide-react";

interface ErrorStateProps {
  message?: string;
  onRetry?: () => void;
}

/** Displays an inline error message with an optional Retry button. */
export function ErrorState({
  message = "Something went wrong loading this data.",
  onRetry,
}: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-[#4a6555]">
      <div className="w-12 h-12 rounded-2xl bg-red-500/5 border border-red-500/10 flex items-center justify-center mb-4">
        <AlertTriangle className="h-5 w-5 text-red-400/60" />
      </div>
      <p className="text-[13px] mb-4 text-center max-w-[280px] leading-relaxed">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="px-4 py-1.5 text-[12px] font-medium rounded-lg bg-white/[0.04] border border-white/[0.08] text-[#c5dace] hover:bg-white/[0.06] hover:border-[#4ade80]/20 transition-all duration-200"
        >
          Retry
        </button>
      )}
    </div>
  );
}
