'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ProtectedRoute } from '@/lib/auth-context';
import Link from 'next/link';

export default function AddSourcePage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [validationInfo, setValidationInfo] = useState<any>(null);
  const [formData, setFormData] = useState({
    url: '',
    type: 'github_raw' as 'github_raw' | 'subscription_base64',
    name: '',
    description: '',
    is_paid: false,
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target as any;
    setFormData({
      ...formData,
      [name]: type === 'checkbox' ? (e.target as HTMLInputElement).checked : value,
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setValidationInfo(null);

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/my-sources`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(formData),
      });

      if (response.ok) {
        const data = await response.json();
        setValidationInfo(data.validation);
        setTimeout(() => {
          router.push('/dashboard');
        }, 1500);
      } else {
        const data = await response.json();
        setError(data.detail || 'Failed to add source');
      }
    } catch (err) {
      setError('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-gray-50 py-12 px-4">
        <div className="max-w-2xl mx-auto">
          <div className="mb-6">
            <Link href="/dashboard" className="text-blue-600 hover:text-blue-700">
              ← Back to Dashboard
            </Link>
          </div>

          <div className="bg-white rounded-lg shadow-md p-8">
            <h1 className="text-3xl font-bold mb-2">Add Proxy Source</h1>
            <p className="text-gray-600 mb-6">Share a proxy list with the community</p>

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
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
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
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
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
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
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
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
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
                  className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
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
                  className="flex-1 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed font-medium transition"
                >
                  {loading ? 'Validating...' : 'Add Source'}
                </button>
                <button
                  type="button"
                  onClick={() => router.back()}
                  className="flex-1 px-6 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 font-medium transition"
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
