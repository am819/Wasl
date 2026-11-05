import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

interface Analytics {
  period: string;
  total_orders: number;
  total_delivery_fees_egp: number;
  total_platform_commission_egp: number;
  delivered_orders: number;
  cancelled_orders: number;
  average_rating: number;
}

export default function AnalyticsPage() {
  const [data, setData] = useState<Analytics | null>(null);
  const [period, setPeriod] = useState("week");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    apiFetch<Analytics>(`/api/v1/merchants/analytics?period=${period}`)
      .then((res) => {
        if (res.success && res.data) setData(res.data);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [period]);

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="mx-auto max-w-3xl">
        <h1 className="text-2xl font-bold text-gray-900">Analytics</h1>

        <div className="mt-4 flex gap-2">
          {["today", "week", "month"].map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`rounded-md px-3 py-1 text-sm ${
                period === p
                  ? "bg-blue-600 text-white"
                  : "bg-white border border-gray-300 text-gray-600"
              }`}
            >
              {p.charAt(0).toUpperCase() + p.slice(1)}
            </button>
          ))}
        </div>

        {loading ? (
          <p className="mt-6 text-gray-500">Loading…</p>
        ) : data ? (
          <div className="mt-6 grid grid-cols-2 gap-4">
            {[
              { label: "Total Orders", value: data.total_orders },
              {
                label: "Delivery Fees (EGP)",
                value: data.total_delivery_fees_egp.toFixed(2),
              },
              {
                label: "Platform Commission (EGP)",
                value: data.total_platform_commission_egp.toFixed(2),
              },
              { label: "Delivered", value: data.delivered_orders },
              { label: "Cancelled", value: data.cancelled_orders },
              {
                label: "Average Rating",
                value: data.average_rating.toFixed(2),
              },
            ].map((m) => (
              <div
                key={m.label}
                className="rounded-lg bg-white p-4 shadow"
              >
                <p className="text-sm text-gray-500">{m.label}</p>
                <p className="mt-1 text-2xl font-bold text-gray-900">
                  {m.value}
                </p>
              </div>
            ))}
          </div>
        ) : (
          <p className="mt-6 text-gray-500">No data available.</p>
        )}
      </div>
    </div>
  );
}
