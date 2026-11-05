import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

interface Task {
  order_id: number;
  order_number: string;
  merchant_name: string;
  customer_name: string;
  pickup_address_line1: string;
  delivery_address_line1: string;
  total_egp: number;
  assignment_status: string;
}

export default function DriverTasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch<{ tasks: Task[]; count: number }>("/api/v1/drivers/tasks")
      .then((res) => {
        if (res.success && res.data) setTasks(res.data.tasks);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  async function accept(orderId: number) {
    await apiFetch(`/api/v1/drivers/tasks/${orderId}/accept`, { method: "POST" });
    window.location.reload();
  }

  async function reject(orderId: number) {
    await apiFetch(`/api/v1/drivers/tasks/${orderId}/reject`, {
      method: "POST",
      body: JSON.stringify({ reason: "Unable to accept" }),
    });
    window.location.reload();
  }

  async function updateStatus(orderId: number, status: string) {
    await apiFetch(`/api/v1/drivers/tasks/${orderId}/status`, {
      method: "PUT",
      body: JSON.stringify({ status }),
    });
    window.location.reload();
  }

  if (loading) return <p className="p-8 text-gray-500">Loading…</p>;

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="mx-auto max-w-3xl">
        <h1 className="text-2xl font-bold text-gray-900">My Tasks</h1>
        {tasks.length === 0 ? (
          <p className="mt-4 text-gray-500">No tasks assigned.</p>
        ) : (
          <div className="mt-4 space-y-4">
            {tasks.map((t) => (
              <div key={t.order_id} className="rounded-lg bg-white p-4 shadow">
                <div className="flex justify-between">
                  <span className="font-semibold text-gray-900">
                    {t.order_number}
                  </span>
                  <span className="text-sm capitalize text-gray-500">
                    {t.assignment_status}
                  </span>
                </div>
                <p className="mt-2 text-sm text-gray-600">
                  From: {t.merchant_name} → {t.customer_name}
                </p>
                <p className="text-sm text-gray-600">
                  Pickup: {t.pickup_address_line1}
                </p>
                <p className="text-sm text-gray-600">
                  Delivery: {t.delivery_address_line1}
                </p>
                <p className="text-sm font-medium text-gray-700">
                  Total: {t.total_egp.toFixed(2)} EGP
                </p>
                {t.assignment_status === "assigned" && (
                  <div className="mt-3 flex gap-2">
                    <button
                      onClick={() => accept(t.order_id)}
                      className="rounded-md bg-green-600 px-3 py-1 text-sm text-white"
                    >
                      Accept
                    </button>
                    <button
                      onClick={() => reject(t.order_id)}
                      className="rounded-md bg-red-500 px-3 py-1 text-sm text-white"
                    >
                      Reject
                    </button>
                  </div>
                )}
                {t.assignment_status === "accepted" && (
                  <button
                    onClick={() => updateStatus(t.order_id, "picked_up")}
                    className="mt-3 rounded-md bg-blue-600 px-3 py-1 text-sm text-white"
                  >
                    Mark picked up
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
