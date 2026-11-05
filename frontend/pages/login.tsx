import { useState, useEffect, type FormEvent } from "react";
import { useRouter } from "next/router";
import Link from "next/link";
import AuthLayout from "@/components/AuthLayout";
import { publicPost } from "@/lib/api";
import { saveTokens, isLoggedIn } from "@/lib/auth";

interface LoginData {
  user_id: number;
  email: string;
  role: string;
  token: string;
  refresh_token: string;
  expires_in: number;
}

export default function LoginPage() {
  const router = useRouter();
  const { registered } = router.query;

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Already logged in — redirect away
  useEffect(() => {
    if (isLoggedIn()) {
      void router.replace("/");
    }
  }, [router]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const res = await publicPost<LoginData>("/api/v1/auth/login", {
        email,
        password,
      });

      if (!res.success || !res.data || res.error) {
        setError(res.error?.message ?? "Login failed");
        return;
      }

      const { token, refresh_token, expires_in, role } = res.data;
      saveTokens(token, refresh_token, expires_in);

      // Redirect based on role
      const destination =
        role === "admin"
          ? "/admin/dashboard"
          : role === "driver"
          ? "/driver/dashboard"
          : "/merchant/dashboard";

      await router.push(destination);
    } catch {
      setError("Unable to connect to the server. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthLayout title="Sign in to WASL">
      {registered === "1" && (
        <div
          role="status"
          className="mb-4 text-sm text-green-700 bg-green-50 rounded p-2"
        >
          Account created. You can sign in once an admin approves your account.
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        {/* Email */}
        <div>
          <label
            htmlFor="email"
            className="block text-sm font-medium text-gray-700"
          >
            Email address
          </label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>

        {/* Password */}
        <div>
          <label
            htmlFor="password"
            className="block text-sm font-medium text-gray-700"
          >
            Password
          </label>
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>

        {/* Error */}
        {error && (
          <p role="alert" className="text-sm text-red-600 bg-red-50 rounded p-2">
            {error}
          </p>
        )}

        {/* Submit */}
        <button
          type="submit"
          disabled={loading}
          className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? "Signing in…" : "Sign in"}
        </button>

        <p className="text-center text-sm text-gray-500">
          No account yet?{" "}
          <Link href="/register" className="text-blue-600 hover:underline">
            Register
          </Link>
        </p>
      </form>
    </AuthLayout>
  );
}
