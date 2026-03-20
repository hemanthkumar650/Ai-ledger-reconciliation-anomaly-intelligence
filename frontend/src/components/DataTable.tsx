"use client";

interface DataTableColumn<T> {
  key: keyof T;
  label: string;
  render?: (value: T[keyof T], row: T) => React.ReactNode;
  width?: string;
  align?: "left" | "center" | "right";
}

interface DataTableProps<T> {
  columns: DataTableColumn<T>[];
  data: T[];
  isLoading?: boolean;
  onRowClick?: (row: T) => void;
}

export function DataTable<T extends object>({
  columns,
  data,
  isLoading,
  onRowClick,
}: DataTableProps<T>) {
  if (isLoading) {
    return (
      <div className="space-y-3 w-full">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-12 bg-gray-200 rounded animate-pulse" />
        ))}
      </div>
    );
  }

  return (
    <div className="overflow-x-auto border border-gray-200 rounded-lg">
      <table className="w-full">
        <thead className="bg-gray-50 border-b border-gray-200">
          <tr>
            {columns.map((col) => (
              <th
                key={String(col.key)}
                className="px-6 py-3 text-left text-sm font-semibold text-gray-900"
                style={{ width: col.width, textAlign: col.align }}
              >
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {data.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="px-6 py-12 text-center text-gray-500">
                No data found
              </td>
            </tr>
          ) : (
            data.map((row, idx) => (
              <tr
                key={idx}
                className={`border-b border-gray-200 ${
                  onRowClick ? "cursor-pointer hover:bg-gray-50" : ""
                }`}
                onClick={() => onRowClick?.(row)}
              >
                {columns.map((col) => (
                  <td
                    key={String(col.key)}
                    className="px-6 py-4 text-sm text-gray-700"
                    style={{ textAlign: col.align }}
                  >
                    {col.render
                      ? col.render(row[col.key], row)
                      : String(row[col.key])}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
