import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import Link from "next/link";
import { apiFetch } from "@/lib/api";

interface OrderDetail {
  order: {
    id: number;
    order_number: string;
    customer_name: string;
    customer_phone: string;
    pickup_address_line1: string;
    delivery_address_line1: string;
    status: string;
    subtotal_egp: number;
    delivery_fee_egp: number;
    total_egp: number;
    created_at: string;
  };
  items: Array<{
    id: number;
    item_name: string;
    quantity: number;
    unit_price_egp: number;
    subtotal_egp: number;
  }>;
  status_history: Array<{
    id: number;
    previous_status: string | null;
    new_status: string;
    reason: string | null;
    created_at: string;
  }>;
  driver: { full_name: string; vehicle_type: string } | null;
}

export default function OrderDetailPage() {
  const router = useRouter();
  const { id } = router.query;
  const [detail, setDetail] = useState<OrderDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    apiFetch<OrderDetail>(`/api/v1/merchants/orders/${id}`)
      .then((res) => {
        if (res.success && res.data) setDetail(res.data);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <p className="p-8 text-gray-500">Loading…</p>;
  if (!detail) return <p className="p-8 text-gray-500">Order not found.</p>;

  const o = detail.order;
  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="mx-auto max-w-3xl">
        <Link
          href="/merchant/orders"
          className="text-sm text-blue-600 hover:underline"
        >
          ← Back to orders
        </Link>
        <h1 className="mt-2 text-2xl font-bold text-gray-900">
          {o.order_number}
        </h1>
        <p className="text-sm text-gray-500 capitalize">{o.status}</p>

        <div className="mt-6 space-y-6">
          {/* Customer info */}
          <div className="rounded-lg bg-white p-4 shadow">
            <h2 className="font-semibold text-gray-700">Customer</h2>
            <dl className="mt-2 grid grid-cols-2 gap-2 text-sm">
              <dt className="text-gray-500">Name</dt>
              <dd className="text-gray-900">{o.customer_name}</dd>
              <dt className="text-gray-500">Phone</dt>
              <dd className="text-gray-900">{o.customer_phone}</dd>
              <dt className="text-gray-500">Pickup</dt>
              <dd className="text-gray-900">{o.pickup_address_line1}</dd>
              <dt className="text-gray-500">Delivery</dt>
              <dd className="text-gray-900">{o.delivery_address_line1}</dd>
            </dl>
          </div>

          {/* Items */}
          <div className="rounded-lg bg-white p-4 shadow">
            <h2 className="font-semibold text-gray-700">Items</h2>
            <table className="mt-2 w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500">
                  <th className="py-1">Item</th>
                  <th className="py-1">Qty</th>
                  <th className="py-1">Unit (EGP)</th>
                  <th className="py-1">Subtotal (EGP)</th>
                </tr>
              </thead>
              <tbody>
                {detail.items.map((it) => (
                  <tr key={it.id} className="border-t border-gray-100">
                    <td className="py-1">{it.item_name}</td>
                    <td className="py-1">{it.quantity}</td>
                    <td className="py-1">{it.unit_price_egp.toFixed(2)}</td>
                    <td className="py-1">{it.subtotal_egp.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="mt-3 text-sm text-gray-700">
              Subtotal: {o.subtotal_egp.toFixed(2)} EGP | Delivery:{" "}
              {o.delivery_fee_egp.toFixed(2)} EGP | Total:{" "}
              {o.total_egp.toFixed(2)} EGP
            </div>
          </div>

          {/* Status history */}
          <div className="rounded-lg bg-white p-4 shadow">
            <h2 className="font-semibold text-gray-700">Status History</h2>
            <ol className="mt-2 space-y-1 text-sm">
              {detail.status_history.map((h) => (
                <li key={h.id} className="text-gray-600">
                  <span className="font-medium">{h.new_status}</span>
                  {h.reason ? ` — ${h.reason}` : ""}
                  <span className="text-gray-400">
                    {" "}({new Date(h.created_at).toLocaleString()})
                  </span>
                </li>
              ))}
            </ol>
          </div>

          {/* Driver info */}
          {detail.driver && (
            <div className="rounded-lg bg-white p-4 shadow">
              <h2 className="font-semibold text-gray-700">Driver</h2>
              <p className="mt-2 text-sm text-gray-600">
                {detail.driver.full_name} ({detail.driver.vehicle_type})
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
