interface SpinnerProps {
  size?: "sm" | "md" | "lg";
  className?: string;
}

const sizeStyles = { sm: "h-4 w-4", md: "h-6 w-6", lg: "h-8 w-8" };

/** Loading spinner for async states. */
export function Spinner({ size = "md", className = "" }: SpinnerProps) {
  return (
    <div
      className={`animate-spin rounded-full border-2 border-[#2d4a38] border-t-[#4ade80] ${sizeStyles[size]} ${className}`}
      role="status"
      aria-label="Loading"
    />
  );
}
