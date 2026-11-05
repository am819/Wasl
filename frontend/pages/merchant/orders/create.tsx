import { useState, type FormEvent } from "react";
import { useRouter } from "next/router";
import { apiFetch } from "@/lib/api";

interface OrderItem {
  item_name: string;
  quantity: number;
  unit_price_egp: number;
}

export default function CreateOrderPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [customer, setCustomer] = useState({
    customer_name: "",
    customer_phone: "",
    pickup_address_line1: "",
    delivery_address_line1: "",
    delivery_notes: "",
  });

  const [items, setItems] = useState<OrderItem[]>([
    { item_name: "", quantity: 1, unit_price_egp: 0 },
  ]);

  function addItem() {
    setItems((i) => [
      ...i,
      { item_name: "", quantity: 1, unit_price_egp: 0 },
    ]);
  }

  function updateItem(idx: number, field: keyof OrderItem, val: string | number) {
    setItems((arr) =>
      arr.map((it, i) =>
        i === idx ? { ...it, [field]: val } : it
      )
    );
  }

  function removeItem(idx: number) {
    setItems((arr) => arr.filter((_, i) => i !== idx));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch("/api/v1/merchants/orders", {
        method: "POST",
        body: JSON.stringify({
          ...customer,
          items: items.filter((i) => i.item_name.trim()),
        }),
      });
      if (!res.success || res.error) {
        setError(res.error?.message ?? "Failed to create order");
        return;
      }
      await router.push("/merchant/orders");
    } catch {
      setError("Unable to connect to the server.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="mx-auto max-w-2xl">
        <h1 className="text-2xl font-bold text-gray-900">Create Order</h1>
        <form onSubmit={handleSubmit} className="mt-6 space-y-6" noValidate>
          {/* Customer info */}
          <div className="space-y-3 rounded-lg bg-white p-4 shadow">
            <h2 className="font-semibold text-gray-700">Customer</h2>
            <div>
              <label className="block text-sm text-gray-600">Name</label>
              <input
                type="text"
                required
                value={customer.customer_name}
                onChange={(e) =>
                  setCustomer({ ...customer, customer_name: e.target.value })
                }
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-600">Phone</label>
              <input
                type="tel"
                required
                value={customer.customer_phone}
                onChange={(e) =>
                  setCustomer({ ...customer, customer_phone: e.target.value })
                }
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-600">Pickup address</label>
              <input
                type="text"
                required
                value={customer.pickup_address_line1}
                onChange={(e) =>
                  setCustomer({
                    ...customer,
                    pickup_address_line1: e.target.value,
                  })
                }
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-600">Delivery address</label>
              <input
                type="text"
                required
                value={customer.delivery_address_line1}
                onChange={(e) =>
                  setCustomer({
                    ...customer,
                    delivery_address_line1: e.target.value,
                  })
                }
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-600">Notes</label>
              <input
                type="text"
                value={customer.delivery_notes}
                onChange={(e) =>
                  setCustomer({ ...customer, delivery_notes: e.target.value })
                }
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
          </div>

          {/* Items */}
          <div className="space-y-3 rounded-lg bg-white p-4 shadow">
            <h2 className="font-semibold text-gray-700">Items</h2>
            {items.map((item, idx) => (
              <div key={idx} className="flex gap-2">
                <input
                  type="text"
                  placeholder="Item name"
                  value={item.item_name}
                  onChange={(e) => updateItem(idx, "item_name", e.target.value)}
                  className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm"
                />
                <input
                  type="number"
                  min={1}
                  placeholder="Qty"
                  value={item.quantity}
                  onChange={(e) =>
                    updateItem(idx, "quantity", parseInt(e.target.value, 10) || 1)
                  }
                  className="w-20 rounded-md border border-gray-300 px-3 py-2 text-sm"
                />
                <input
                  type="number"
                  min={0}
                  step="0.01"
                  placeholder="Price"
                  value={item.unit_price_egp}
                  onChange={(e) =>
                    updateItem(idx, "unit_price_egp", parseFloat(e.target.value) || 0)
                  }
                  className="w-28 rounded-md border border-gray-300 px-3 py-2 text-sm"
                />
                {items.length > 1 && (
                  <button
                    type="button"
                    onClick={() => removeItem(idx)}
                    className="text-red-500 text-sm"
                  >
                    Remove
                  </button>
                )}
              </div>
            ))}
            <button
              type="button"
              onClick={addItem}
              className="text-sm text-blue-600 hover:underline"
            >
              + Add item
            </button>
          </div>

          {error && (
            <p role="alert" className="text-sm text-red-600 bg-red-50 rounded p-2">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? "Creating…" : "Create order"}
          </button>
        </form>
      </div>
    </div>
  );
}
