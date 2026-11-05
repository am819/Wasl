import { useState } from "react";

interface Props {
  initialOnline: boolean;
  driverId: number;
}

export default function AvailabilityToggle({ initialOnline }: Props) {
  const [isOnline, setIsOnline] = useState(initialOnline);

  async function toggle() {
    const res = await fetch("/api/v1/drivers/availability", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ is_online: !isOnline }),
    });
    if (res.ok) {
      const data = await res.json();
      setIsOnline(data.data.is_online);
    }
  }

  return (
    <button
      onClick={toggle}
      className={`rounded-full px-4 py-2 text-sm font-medium ${
        isOnline
          ? "bg-green-500 text-white"
          : "bg-gray-200 text-gray-600"
      }`}
    >
      {isOnline ? "Online" : "Offline"}
    </button>
  );
}
