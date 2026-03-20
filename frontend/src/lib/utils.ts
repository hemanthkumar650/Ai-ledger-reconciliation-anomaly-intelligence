export const formatCurrency = (amount: number): string => {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  }).format(amount);
};

export const formatPercent = (value: number, decimals: number = 1): string => {
  return (value * 100).toFixed(decimals) + "%";
};

export const formatDate = (dateString: string): string => {
  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(dateString));
};

export const getRiskColor = (riskLevel: string): string => {
  switch (riskLevel) {
    case "High":
      return "text-red-600";
    case "Medium":
      return "text-orange-600";
    case "Low":
      return "text-green-600";
    default:
      return "text-gray-600";
  }
};

export const getRiskBgColor = (riskLevel: string): string => {
  switch (riskLevel) {
    case "High":
      return "bg-red-100 text-red-800";
    case "Medium":
      return "bg-orange-100 text-orange-800";
    case "Low":
      return "bg-green-100 text-green-800";
    default:
      return "bg-gray-100 text-gray-800";
  }
};
