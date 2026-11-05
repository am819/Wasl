import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import Head from "next/head";

interface TrackingData {
  order_number: string;
  status: string;
  customer_name: string;
  delivery_address_line1: string;
  driver_first_name: string | null;
  estimated_delivery_at: string | null;
  actual_delivery_at: string | null;
}

const STATUS_LABELS: Record<string, string> = {
  pending: "Waiting for driver assignment",
  assigned: "Driver assigned",
  picked_up: "Order picked up",
  in_transit: "On the way",
  delivered: "Delivered",
  cancelled: "Cancelled",
};

export default function TrackingPage() {
  const router = useRouter();
  const { token } = router.query;
  const [data, setData] = useState<TrackingData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token || typeof token !== "string") return;
    const apiUrl =
      process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    fetch(`${apiUrl}/api/v1/tracking/${token}`)
      .then(async (res) => {
        if (!res.ok) {
          setError("This tracking link is no longer valid.");
          return null;
        }
        return res.json();
      })
      .then((body) => {
        if (body?.data) setData(body.data);
      })
      .catch(() => setError("Unable to connect to the server."))
      .finally(() => setLoading(false));
  }, [token]);

  if (loading)
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <p className="text-gray-500">Loading…</p>
      </div>
    );

  if (error || !data)
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <Head>
            <title>Tracking — WASL</title>
          </Head>
          <h1 className="text-2xl font-bold text-gray-900">WASL</h1>
          <p className="mt-2 text-gray-500">{error ?? "Order not found"}</p>
        </div>
      </div>
    );

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <Head>
        <title>Track {data.order_number} — WASL</title>
      </Head>
      <div className="mx-auto max-w-md">
        <h1 className="text-center text-2xl font-bold text-gray-900">WASL</h1>
        <p className="text-center text-sm text-gray-500">Delivery Tracking</p>

        <div className="mt-6 rounded-lg bg-white p-6 shadow">
          <div className="text-center">
            <p className="text-sm text-gray-500">Order</p>
            <p className="font-semibold text-gray-900">{data.order_number}</p>
          </div>

          <div className="mt-4">
            <div
              className={`rounded-full px-4 py-2 text-center text-sm font-medium ${
                data.status === "delivered"
                  ? "bg-green-100 text-green-800"
                  : data.status === "cancelled"
                  ? "bg-red-100 text-red-800"
                  : "bg-blue-100 text-blue-800"
              }`}
            >
              {STATUS_LABELS[data.status] ?? data.status}
            </div>
          </div>

          <dl className="mt-4 space-y-2 text-sm">
            <div>
              <dt className="text-gray-500">Customer</dt>
              <dd className="text-gray-900">{data.customer_name}</dd>
            </div>
            <div>
              <dt className="text-gray-500">Delivery address</dt>
              <dd className="text-gray-900">
                {data.delivery_address_line1}
              </dd>
            </div>
            {data.driver_first_name && (
              <div>
                <dt className="text-gray-500">Driver</dt>
                <dd className="text-gray-900">
                  {data.driver_first_name}
                </dd>
              </div>
            )}
            {data.estimated_delivery_at && (
              <div>
                <dt className="text-gray-500">Estimated delivery</dt>
                <dd className="text-gray-900">
                  {new Date(
                    data.estimated_delivery_at
                  ).toLocaleString()}
                </dd>
              </div>
            )}
            {data.actual_delivery_at && (
              <div>
                <dt className="text-gray-500">Delivered at</dt>
                <dd className="text-gray-900">
                  {new Date(
                    data.actual_delivery_at
                  ).toLocaleString()}
                </dd>
              </div>
            )}
          </dl>
        </div>
      </div>
    </div>
  );
}
