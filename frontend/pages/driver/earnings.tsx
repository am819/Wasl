import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

interface Earnings {
  period: string;
  total_earnings_egp: number;
  order_count: number;
  pending_payout_egp: number;
}

export default function DriverEarningsPage() {
  const [data, setData] = useState<Earnings | null>(null);
  const [period, setPeriod] = useState("week");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    apiFetch<Earnings>(`/api/v1/drivers/earnings?period=${period}`)
      .then((res) => {
        if (res.success && res.data) setData(res.data);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [period]);

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="mx-auto max-w-2xl">
        <h1 className="text-2xl font-bold text-gray-900">Earnings</h1>
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
            <div className="rounded-lg bg-white p-4 shadow">
              <p className="text-sm text-gray-500">Total Earnings (EGP)</p>
              <p className="mt-1 text-2xl font-bold text-gray-900">
                {data.total_earnings_egp.toFixed(2)}
              </p>
            </div>
            <div className="rounded-lg bg-white p-4 shadow">
              <p className="text-sm text-gray-500">Deliveries</p>
              <p className="mt-1 text-2xl font-bold text-gray-900">
                {data.order_count}
              </p>
            </div>
            <div className="rounded-lg bg-white p-4 shadow">
              <p className="text-sm text-gray-500">Pending Payout (EGP)</p>
              <p className="mt-1 text-2xl font-bold text-gray-900">
                {data.pending_payout_egp.toFixed(2)}
              </p>
            </div>
          </div>
        ) : (
          <p className="mt-6 text-gray-500">No data available.</p>
        )}
      </div>
    </div>
  );
}
