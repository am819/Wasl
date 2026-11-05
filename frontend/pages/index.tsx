import type { NextPage } from "next";
import Head from "next/head";

const Home: NextPage = () => {
  return (
    <>
      <Head>
        <title>WASL — Delivery Management</title>
        <meta name="description" content="WASL B2B last-mile delivery platform" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <main className="flex min-h-screen flex-col items-center justify-center bg-gray-50">
        <div className="text-center">
          <h1 className="text-4xl font-bold text-gray-900">WASL</h1>
          <p className="mt-2 text-lg text-gray-500">
            B2B Delivery Management Platform
          </p>
          <p className="mt-4 text-sm text-gray-400">
            Skeleton — Phase 0 complete
          </p>
        </div>
      </main>
    </>
  );
};

export default Home;
