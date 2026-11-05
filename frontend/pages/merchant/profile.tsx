import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import { apiFetch } from "@/lib/api";

interface Profile {
  business_name: string;
  business_phone: string;
  address_line1: string;
  contact_person_name: string;
  status: string;
}

export default function MerchantProfilePage() {
  const router = useRouter();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch<Profile>("/api/v1/merchants/profile")
      .then((res) => {
        if (res.success && res.data) setProfile(res.data);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="p-8 text-gray-500">Loading…</p>;

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="mx-auto max-w-2xl">
        <h1 className="text-2xl font-bold text-gray-900">Merchant Profile</h1>
        {profile ? (
          <dl className="mt-6 space-y-3 text-sm">
            <div>
              <dt className="font-medium text-gray-500">Business name</dt>
              <dd className="text-gray-900">{profile.business_name}</dd>
            </div>
            <div>
              <dt className="font-medium text-gray-500">Phone</dt>
              <dd className="text-gray-900">{profile.business_phone}</dd>
            </div>
            <div>
              <dt className="font-medium text-gray-500">Address</dt>
              <dd className="text-gray-900">{profile.address_line1}</dd>
            </div>
            <div>
              <dt className="font-medium text-gray-500">Contact</dt>
              <dd className="text-gray-900">{profile.contact_person_name}</dd>
            </div>
            <div>
              <dt className="font-medium text-gray-500">Status</dt>
              <dd className="text-gray-900 capitalize">{profile.status}</dd>
            </div>
          </dl>
        ) : (
          <p className="mt-6 text-gray-500">
            No profile yet.{" "}
            <button
              onClick={() => router.push("/merchant/register")}
              className="text-blue-600 hover:underline"
            >
              Create one
            </button>
          </p>
        )}
      </div>
    </div>
  );
}
