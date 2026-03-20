interface KPICardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: "up" | "down" | "neutral";
  icon?: React.ReactNode;
}

export function KPICard({ title, value, subtitle, trend, icon }: KPICardProps) {
  return (
    <div className="bg-white rounded-lg shadow p-6 border border-gray-200 hover:shadow-lg transition">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm text-gray-600 font-medium">{title}</p>
          <p className="text-3xl font-bold text-gray-900 mt-2">{value}</p>
          {subtitle && <p className="text-xs text-gray-500 mt-1">{subtitle}</p>}
        </div>
        {icon && <div className="text-gray-400 text-2xl">{icon}</div>}
      </div>
      {trend && (
        <div
          className={`mt-3 text-xs font-semibold ${
            trend === "up" ? "text-red-600" : trend === "down" ? "text-green-600" : "text-gray-600"
          }`}
        >
          {trend === "up" && "↑"} {trend === "down" && "↓"} {trend === "neutral" && "→"}
        </div>
      )}
    </div>
  );
}
