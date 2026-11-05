import { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";

interface Order {
  id: number;
  order_number: string;
  customer_name: string;
  status: string;
  total_egp: number;
  created_at: string;
}

export default function OrderListPage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");

  useEffect(() => {
    const params = statusFilter ? `?status=${statusFilter}` : "";
    apiFetch<{ orders: Order[]; total_count: number }>(
      `/api/v1/merchants/orders${params}`
    )
      .then((res) => {
        if (res.success && res.data) setOrders(res.data.orders);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [statusFilter]);

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="mx-auto max-w-4xl">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900">Orders</h1>
          <Link
            href="/merchant/orders/create"
            className="text-sm text-blue-600 hover:underline"
          >
            + New order
          </Link>
        </div>

        <div className="mt-4 flex gap-2">
          {["", "pending", "assigned", "delivered", "cancelled"].map((s) => (
            <button
              key={s || "all"}
              onClick={() => setStatusFilter(s)}
              className={`rounded-md px-3 py-1 text-sm ${
                statusFilter === s
                  ? "bg-blue-600 text-white"
                  : "bg-white border border-gray-300 text-gray-600"
              }`}
            >
              {s || "All"}
            </button>
          ))}
        </div>

        {loading ? (
          <p className="mt-6 text-gray-500">Loading…</p>
        ) : (
          <table className="mt-6 w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 text-left text-gray-500">
                <th className="py-2">Order #</th>
                <th className="py-2">Customer</th>
                <th className="py-2">Status</th>
                <th className="py-2">Total (EGP)</th>
                <th className="py-2">Date</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((o) => (
                <tr key={o.id} className="border-b border-gray-100">
                  <td className="py-2">
                    <Link
                      href={`/merchant/orders/${o.id}`}
                      className="text-blue-600 hover:underline"
                    >
                      {o.order_number}
                    </Link>
                  </td>
                  <td className="py-2">{o.customer_name}</td>
                  <td className="py-2 capitalize">{o.status}</td>
                  <td className="py-2">{o.total_egp.toFixed(2)}</td>
                  <td className="py-2">
                    {new Date(o.created_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
