import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

interface PlatformAnalytics {
  period: string;
  total_orders: number;
  delivered_orders: number;
  cancelled_orders: number;
  active_merchants: number;
  active_drivers: number;
  completion_rate: number;
}

export default function AdminDashboardPage() {
  const [data, setData] = useState<PlatformAnalytics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch<PlatformAnalytics>("/api/v1/admin/analytics?period=week")
      .then((res) => {
        if (res.success && res.data) setData(res.data);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="p-8 text-gray-500">Loading…</p>;

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="mx-auto max-w-4xl">
        <h1 className="text-2xl font-bold text-gray-900">Admin Dashboard</h1>
        {data && (
          <div className="mt-6 grid grid-cols-3 gap-4">
            {[
              { label: "Total Orders", value: data.total_orders },
              { label: "Delivered", value: data.delivered_orders },
              { label: "Cancelled", value: data.cancelled_orders },
              { label: "Active Merchants", value: data.active_merchants },
              { label: "Active Drivers", value: data.active_drivers },
              {
                label: "Completion Rate",
                value: `${(data.completion_rate * 100).toFixed(1)}%`,
              },
            ].map((m) => (
              <div key={m.label} className="rounded-lg bg-white p-4 shadow">
                <p className="text-sm text-gray-500">{m.label}</p>
                <p className="mt-1 text-2xl font-bold text-gray-900">
                  {m.value}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
