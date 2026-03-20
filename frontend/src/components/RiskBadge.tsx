import { getRiskBgColor } from "@/lib/utils";

interface RiskBadgeProps {
  level: string;
  size?: "sm" | "md" | "lg";
}

export function RiskBadge({ level, size = "md" }: RiskBadgeProps) {
  const sizeClasses = {
    sm: "px-2 py-1 text-xs font-medium rounded",
    md: "px-3 py-1 text-sm font-semibold rounded-full",
    lg: "px-4 py-2 text-base font-bold rounded-lg",
  };

  return <span className={`${sizeClasses[size]} ${getRiskBgColor(level)}`}>{level}</span>;
}
