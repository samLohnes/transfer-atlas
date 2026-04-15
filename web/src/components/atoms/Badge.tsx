interface BadgeProps {
  children: React.ReactNode;
  variant?: "default" | "success" | "warning" | "danger";
  className?: string;
}

const variantStyles: Record<NonNullable<BadgeProps["variant"]>, string> = {
  default: "bg-[#243d2e] text-[#8fa898]",
  success: "bg-green-900/40 text-green-400",
  warning: "bg-amber-900/40 text-amber-400",
  danger: "bg-red-900/40 text-red-400",
};

/** Small colored label for status indicators. */
export function Badge({ children, variant = "default", className = "" }: BadgeProps) {
  return (
    <span className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ${variantStyles[variant]} ${className}`}>
      {children}
    </span>
  );
}
