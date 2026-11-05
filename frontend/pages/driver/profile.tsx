import { useEffect, useState } from "react";
import Link from "next/link";
import AvailabilityToggle from "@/components/AvailabilityToggle";
import { apiFetch } from "@/lib/api";

interface DriverProfile {
  id: number;
  full_name: string;
  vehicle_type: string;
  vehicle_plate_number: string | null;
  is_online: boolean;
  is_on_delivery: boolean;
  stats: {
    total_deliveries: number;
    total_earnings_egp: number;
    average_rating: number;
    cancellation_rate: number;
  };
  status: string;
}

export default function DriverProfilePage() {
  const [profile, setProfile] = useState<DriverProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch<DriverProfile>("/api/v1/drivers/profile")
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
        <h1 className="text-2xl font-bold text-gray-900">Driver Profile</h1>
        {profile ? (
          <>
            <dl className="mt-6 space-y-3 text-sm">
              <div>
                <dt className="font-medium text-gray-500">Name</dt>
                <dd className="text-gray-900">{profile.full_name}</dd>
              </div>
              <div>
                <dt className="font-medium text-gray-500">Vehicle</dt>
                <dd className="text-gray-900 capitalize">
                  {profile.vehicle_type}
                  {profile.vehicle_plate_number
                    ? ` (${profile.vehicle_plate_number})`
                    : ""}
                </dd>
              </div>
              <div>
                <dt className="font-medium text-gray-500">Status</dt>
                <dd className="text-gray-900 capitalize">{profile.status}</dd>
              </div>
              <div>
                <dt className="font-medium text-gray-500">Deliveries</dt>
                <dd className="text-gray-900">
                  {profile.stats.total_deliveries}
                </dd>
              </div>
              <div>
                <dt className="font-medium text-gray-500">
                  Total Earnings (EGP)
                </dt>
                <dd className="text-gray-900">
                  {profile.stats.total_earnings_egp.toFixed(2)}
                </dd>
              </div>
              <div>
                <dt className="font-medium text-gray-500">Rating</dt>
                <dd className="text-gray-900">
                  {profile.stats.average_rating.toFixed(2)}
                </dd>
              </div>
            </dl>
            <div className="mt-6">
              {profile.status === "approved" && (
                <AvailabilityToggle
                  initialOnline={profile.is_online}
                  driverId={profile.id}
                />
              )}
            </div>
          </>
        ) : (
            <p className="mt-6 text-gray-500">
              No profile yet.{" "}
              <Link href="/driver/register" className="text-blue-600 hover:underline">
                Create one
              </Link>
            </p>
        )}
      </div>
    </div>
  );
}
