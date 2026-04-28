'use client';

import { useState } from 'react';
import { Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { ProtectedRoute } from '@/lib/auth-context';
import Link from 'next/link';
import { getFullUrl } from '@/lib/constants';
import { api, type SourceCreateResponse, type SourceType } from '@/lib/api';

interface SourceFormData {
  url: string;
  type: Extract<SourceType, 'github_raw' | 'subscription_base64'>;
  name: string;
  description: string;
  is_paid: boolean;
}

function AddSourceContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const isPremiumMode = searchParams.get('premium') === 'true';
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [validationInfo, setValidationInfo] = useState<SourceCreateResponse['validation'] | null>(null);
  const [formData, setFormData] = useState<SourceFormData>({
    url: '',
    type: 'github_raw',
    name: '',
    description: '',
    is_paid: isPremiumMode,
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const target = e.target;
    const fieldName = target.name as keyof SourceFormData;
    const fieldValue = target instanceof HTMLInputElement && target.type === 'checkbox'
      ? target.checked
      : target.value;
    setFormData({
      ...formData,
      [fieldName]: fieldValue,
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setValidationInfo(null);

    try {
      const data = await api.createMySource({
        ...formData,
        name: formData.name.trim() || undefined,
        description: formData.description.trim() || undefined,
      });
      setValidationInfo(data.validation);
      setTimeout(() => {
        router.push(getFullUrl('/dashboard'));
      }, 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const cardBackground = '#FFFFFF';
  const pixelFont = "'Press Start 2P', 'Courier New', monospace";

  return (
    <ProtectedRoute>
      <div className="min-h-screen py-12 px-4" style={{ backgroundColor: 'var(--light-bg)' }}>
        <div className="max-w-3xl mx-auto">
          <div className="mb-6">
            <Link href={getFullUrl("/dashboard")} className="font-bold underline" style={{ color: 'var(--retro-pink)', fontFamily: pixelFont }}>
              ← Back to Dashboard
            </Link>
          </div>

          <div className="rounded-2xl p-6 md:p-8" style={{ backgroundColor: cardBackground, border: '3px solid #000000', boxShadow: '6px 6px 0px #000000' }}>
            <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4 mb-6">
              <div>
                <h1 className="text-4xl md:text-5xl font-bold mb-2" style={{ fontFamily: "'Bangers', cursive", color: isPremiumMode ? 'var(--retro-yellow)' : 'var(--retro-pink)', textShadow: '3px 3px 0px #000000' }}>
                  {isPremiumMode ? 'Add Premium Source' : 'Add Proxy Source'}
                </h1>
                <p className="text-sm text-gray-700" style={{ fontFamily: pixelFont }}>
                  {isPremiumMode ? 'Register a paid or private feed while still validating it before use.' : 'Share a public proxy list with the community.'}
                </p>
              </div>
              {isPremiumMode && (
                <span className="px-4 py-2 rounded-lg font-bold" style={{ backgroundColor: 'var(--retro-yellow)', color: '#000000', border: '3px solid #000000', boxShadow: '3px 3px 0px #000000', fontFamily: pixelFont }}>
                  ⭐ Premium
                </span>
              )}
            </div>

            {error && (
              <div className="mb-4 rounded-md bg-red-50 p-4 text-sm text-red-800">
                {error}
              </div>
            )}

            {validationInfo && (
              <div className="mb-4 rounded-md bg-green-50 p-4">
                <p className="text-sm text-green-800 font-medium">✅ Source validated successfully!</p>
                <p className="text-sm text-green-700 mt-1">Found {validationInfo.proxy_count} proxies</p>
                <p className="text-xs text-green-600 mt-2">Redirecting to dashboard...</p>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-6">
              <div>
                <label htmlFor="url" className="block text-sm font-medium text-gray-700 mb-2">
                  Source URL *
                </label>
                <input
                  id="url"
                  type="url"
                  name="url"
                  required
                  className="w-full px-4 py-3 rounded-lg focus:outline-none"
                  style={{ border: '3px solid #000000', boxShadow: '3px 3px 0px #000000', fontFamily: pixelFont }}
                  value={formData.url}
                  onChange={handleChange}
                  placeholder="https://raw.githubusercontent.com/..."
                />
                <p className="mt-1 text-xs text-gray-500">
                  Must be publicly accessible and contain valid proxy entries
                </p>
              </div>

              <div>
                <label htmlFor="type" className="block text-sm font-medium text-gray-700 mb-2">
                  Source Type *
                </label>
                <select
                  id="type"
                  name="type"
                  className="w-full px-4 py-3 rounded-lg focus:outline-none"
                  style={{ border: '3px solid #000000', boxShadow: '3px 3px 0px #000000', fontFamily: pixelFont }}
                  value={formData.type}
                  onChange={handleChange}
                >
                  <option value="github_raw">GitHub Raw Content</option>
                  <option value="subscription_base64">Subscription (Base64)</option>
                </select>
              </div>

              <div>
                <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-2">
                  Name (optional)
                </label>
                <input
                  id="name"
                  type="text"
                  name="name"
                  className="w-full px-4 py-3 rounded-lg focus:outline-none"
                  style={{ border: '3px solid #000000', boxShadow: '3px 3px 0px #000000', fontFamily: pixelFont }}
                  value={formData.name}
                  onChange={handleChange}
                  placeholder="My Awesome Proxy List"
                />
              </div>

              <div>
                <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-2">
                  Description (optional)
                </label>
                <textarea
                  id="description"
                  name="description"
                  rows={3}
                  className="w-full px-4 py-3 rounded-lg focus:outline-none"
                  style={{ border: '3px solid #000000', boxShadow: '3px 3px 0px #000000', fontFamily: pixelFont }}
                  value={formData.description}
                  onChange={handleChange}
                  placeholder="Tell the community about this source..."
                />
              </div>

              <div className="flex items-center">
                <input
                  id="is_paid"
                  name="is_paid"
                  type="checkbox"
                  className="h-5 w-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  checked={formData.is_paid}
                  onChange={handleChange}
                />
                <label htmlFor="is_paid" className="ml-2 text-sm text-gray-700">
                  This is a paid/premium source
                </label>
              </div>

              <div className="pt-6 flex gap-4">
                <button
                  type="submit"
                  disabled={loading}
                  className="flex-1 px-6 py-3 rounded-lg disabled:bg-gray-400 disabled:cursor-not-allowed font-bold transition"
                  style={{ backgroundColor: 'var(--retro-blue)', color: '#FFFFFF', border: '3px solid #000000', boxShadow: '4px 4px 0px #000000', fontFamily: pixelFont }}
                >
                  {loading ? 'Validating...' : 'Add Source'}
                </button>
                <button
                  type="button"
                  onClick={() => router.back()}
                  className="flex-1 px-6 py-3 rounded-lg hover:bg-gray-50 font-bold transition"
                  style={{ border: '3px solid #000000', boxShadow: '4px 4px 0px #000000', fontFamily: pixelFont }}
                >
                  Cancel
                </button>
              </div>
            </form>

            <div className="mt-8 p-4 bg-blue-50 rounded-lg border border-blue-200">
              <h3 className="font-semibold text-blue-900 mb-2">📋 Source Requirements:</h3>
              <ul className="text-sm text-blue-800 space-y-1">
                <li>✓ Source must be publicly accessible (no auth required)</li>
                <li>✓ Must contain valid proxy entries (IP:PORT format)</li>
                <li>✓ GitHub sources must be raw content URLs</li>
                <li>✓ Will be validated before acceptance</li>
                <li>✓ Validated proxies will be automatically scraped</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}

export default function AddSourcePage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: 'var(--light-bg)' }}>
          <div className="text-xl animate-pulse" style={{ fontFamily: "'Press Start 2P', 'Courier New', monospace" }}>
            Loading source form...
          </div>
        </div>
      }
    >
      <AddSourceContent />
    </Suspense>
  );
}
