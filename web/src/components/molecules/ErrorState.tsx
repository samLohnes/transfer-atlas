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
    <div className="flex flex-col items-center justify-center py-16 text-[#8fa898]">
      <AlertTriangle className="h-12 w-12 mb-4 opacity-40" />
      <p className="text-sm mb-3">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="px-3 py-1.5 text-sm rounded-md bg-[#243d2e] border border-[#2d4a38] text-[#4ade80] hover:bg-[#2d4a38] transition-colors"
        >
          Retry
        </button>
      )}
    </div>
  );
}
