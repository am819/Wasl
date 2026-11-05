import { useState, type FormEvent } from "react";
import { useRouter } from "next/router";
import AuthLayout from "@/components/AuthLayout";
import { apiFetch } from "@/lib/api";

export default function MerchantRegisterPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [form, setForm] = useState({
    business_name: "",
    business_phone: "",
    address_line1: "",
    contact_person_name: "",
  });

  function update<K extends keyof typeof form>(k: K, v: string) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch("/api/v1/merchants/profile", {
        method: "POST",
        body: JSON.stringify(form),
      });
      if (!res.success || res.error) {
        setError(res.error?.message ?? "Registration failed");
        return;
      }
      await router.push("/merchant/profile");
    } catch {
      setError("Unable to connect to the server.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthLayout title="Merchant Profile Setup">
      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        <div>
          <label className="block text-sm font-medium text-gray-700">
            Business name
          </label>
          <input
            type="text"
            required
            value={form.business_name}
            onChange={(e) => update("business_name", e.target.value)}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">
            Business phone
          </label>
          <input
            type="tel"
            required
            value={form.business_phone}
            onChange={(e) => update("business_phone", e.target.value)}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">
            Address
          </label>
          <input
            type="text"
            required
            value={form.address_line1}
            onChange={(e) => update("address_line1", e.target.value)}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">
            Contact person name
          </label>
          <input
            type="text"
            required
            value={form.contact_person_name}
            onChange={(e) => update("contact_person_name", e.target.value)}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
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
          className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
        >
          {loading ? "Saving…" : "Create profile"}
        </button>
      </form>
    </AuthLayout>
  );
}
