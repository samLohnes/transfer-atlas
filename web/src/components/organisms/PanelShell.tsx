import { X } from "lucide-react";
import { Spinner } from "@/components/atoms/Spinner";
import { ErrorState } from "@/components/molecules/ErrorState";

interface PanelShellProps {
  isOpen: boolean;
  onClose: () => void;
  isLoading: boolean;
  error: string | null;
  onRetry: () => void;
  children: React.ReactNode;
}

/** Reusable slide-in panel shell with close button, loading, and error states. */
export function PanelShell({ isOpen, onClose, isLoading, error, onRetry, children }: PanelShellProps) {
  return (
    <div
      className={`shrink-0 border-l border-white/[0.06] bg-[#0c1a12] overflow-y-auto transition-all duration-300 ease-out z-40 ${
        isOpen ? "w-[35vw] min-w-[400px] max-w-[600px]" : "w-0 min-w-0 max-w-0"
      }`}
    >
      {isOpen && (
        <div className="relative">
          <button
            onClick={onClose}
            className="absolute top-4 right-4 p-1.5 rounded-lg text-[#6b8a78] hover:text-[#e8f0ec] hover:bg-white/[0.05] transition-all z-10"
          >
            <X className="h-4 w-4" />
          </button>

          {isLoading ? (
            <div className="flex justify-center py-20"><Spinner size="lg" /></div>
          ) : error ? (
            <div className="p-6"><ErrorState message={error} onRetry={onRetry} /></div>
          ) : (
            children
          )}
        </div>
      )}
    </div>
  );
}
