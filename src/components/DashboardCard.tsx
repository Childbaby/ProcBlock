import { ReactNode } from "react";

interface DashboardCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: ReactNode;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  status?: "verified" | "warning" | "critical" | "info" | "neutral";
}

export function DashboardCard({
  title,
  value,
  subtitle,
  icon,
  trend,
  status,
}: DashboardCardProps) {
  const statusColorMap = {
    verified: "text-status-verified",
    warning: "text-status-warning",
    critical: "text-status-critical",
    info: "text-status-info",
    neutral: "text-status-neutral",
  };

  return (
    <article className="clinical-card-hover">
      <div className="flex items-start justify-between mb-3">
        <h3 className="text-sm font-medium text-navy-500 uppercase tracking-wide">
          {title}
        </h3>
        {icon && <span className="text-navy-400">{icon}</span>}
      </div>

      <div className="flex items-baseline gap-2">
        <span
          className={`text-display-sm ${status ? statusColorMap[status] : "text-navy-800"}`}
        >
          {value}
        </span>
        {trend && (
          <span
            className={`text-sm font-medium ${trend.isPositive ? "text-status-verified" : "text-status-critical"}`}
          >
            {trend.isPositive ? "↑" : "↓"} {Math.abs(trend.value)}%
          </span>
        )}
      </div>

      {subtitle && <p className="mt-2 text-xs text-navy-400">{subtitle}</p>}
    </article>
  );
}
