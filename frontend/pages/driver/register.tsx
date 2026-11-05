import { useState, type FormEvent } from "react";
import { useRouter } from "next/router";
import AuthLayout from "@/components/AuthLayout";
import { apiFetch } from "@/lib/api";

export default function DriverRegisterPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    full_name: "",
    national_id_number: "",
    vehicle_type: "motorcycle",
    vehicle_plate_number: "",
  });

  function update(k: string, v: string) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch("/api/v1/drivers/profile", {
        method: "POST",
        body: JSON.stringify(form),
      });
      if (!res.success || res.error) {
        setError(res.error?.message ?? "Registration failed");
        return;
      }
      await router.push("/driver/profile");
    } catch {
      setError("Unable to connect to the server.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthLayout title="Driver Profile Setup">
      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        <div>
          <label className="block text-sm font-medium text-gray-700">
            Full name
          </label>
          <input
            type="text"
            required
            value={form.full_name}
            onChange={(e) => update("full_name", e.target.value)}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">
            National ID number
          </label>
          <input
            type="text"
            required
            value={form.national_id_number}
            onChange={(e) => update("national_id_number", e.target.value)}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">
            Vehicle type
          </label>
          <select
            value={form.vehicle_type}
            onChange={(e) => update("vehicle_type", e.target.value)}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          >
            <option value="motorcycle">Motorcycle</option>
            <option value="car">Car</option>
            <option value="van">Van</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">
            Vehicle plate number
          </label>
          <input
            type="text"
            value={form.vehicle_plate_number}
            onChange={(e) => update("vehicle_plate_number", e.target.value)}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          />
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
          {loading ? "Saving…" : "Create profile"}
        </button>
      </form>
    </AuthLayout>
  );
}
