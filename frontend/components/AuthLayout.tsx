import type { ReactNode } from "react";
import Head from "next/head";

interface AuthLayoutProps {
  title: string;
  children: ReactNode;
}

/**
 * Shared wrapper for register and login pages.
 * Centres content on a neutral background.
 */
export default function AuthLayout({ title, children }: AuthLayoutProps) {
  return (
    <>
      <Head>
        <title>{title} — WASL</title>
      </Head>
      <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8">
        <div className="sm:mx-auto sm:w-full sm:max-w-md">
          <h1 className="text-center text-3xl font-bold text-gray-900">
            WASL
          </h1>
          <p className="mt-1 text-center text-sm text-gray-500">
            B2B Delivery Management
          </p>
        </div>
        <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
          <div className="bg-white py-8 px-4 shadow rounded-lg sm:px-10">
            <h2 className="mb-6 text-xl font-semibold text-gray-800">
              {title}
            </h2>
            {children}
          </div>
        </div>
      </div>
    </>
  );
}
