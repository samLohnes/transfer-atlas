interface SpinnerProps {
  size?: "sm" | "md" | "lg";
  className?: string;
}

const sizeStyles = { sm: "h-4 w-4", md: "h-6 w-6", lg: "h-8 w-8" };

/** Loading spinner with green glow. */
export function Spinner({ size = "md", className = "" }: SpinnerProps) {
  return (
    <div
      className={`animate-spin rounded-full border-2 border-white/[0.06] border-t-[#4ade80] ${sizeStyles[size]} ${className}`}
      style={{ filter: "drop-shadow(0 0 4px rgba(74, 222, 128, 0.3))" }}
      role="status"
      aria-label="Loading"
    />
  );
}
