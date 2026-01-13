'use client';

import dynamic from 'next/dynamic';

const HomeClient = dynamic(() => import('./home-client').then(mod => ({ default: mod.HomeClient })), {
  ssr: false,
  loading: () => (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-xl font-bold text-gray-900">Loading 1proxy...</div>
    </div>
  ),
});

export default function Home() {
  return <HomeClient />;
}
