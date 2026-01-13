'use client'

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  return (
    <html>
      <body>
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-900 via-purple-900 to-violet-900">
          <div className="max-w-md w-full mx-4 p-8 bg-gray-800 border-4 border-red-500 rounded-lg shadow-xl">
            <div className="text-center">
              <div className="mb-6 text-6xl">💥</div>
              
              <h2 className="text-2xl font-bold text-red-500 mb-4">
                CRITICAL ERROR
              </h2>
              
              <p className="text-gray-300 mb-6">
                A critical error occurred. Please refresh the page.
              </p>
              
              {error.message && (
                <div className="mb-6 p-4 bg-black/30 border border-red-500/30 rounded">
                  <p className="text-sm text-red-400 font-mono break-words">
                    {error.message}
                  </p>
                </div>
              )}
              
              <div className="flex flex-col gap-3">
                <button
                  onClick={() => reset()}
                  className="w-full px-6 py-3 bg-red-600 text-white font-bold rounded 
                           hover:bg-red-700 transition-all"
                >
                  TRY AGAIN
                </button>
                
                <button
                  onClick={() => window.location.href = '/'}
                  className="w-full px-6 py-3 bg-gray-700 text-white font-bold rounded 
                           hover:bg-gray-600 transition-all border-2 border-gray-600"
                >
                  GO TO HOME
                </button>
              </div>
              
              {error.digest && (
                <p className="mt-4 text-xs text-gray-500 font-mono">
                  Error ID: {error.digest}
                </p>
              )}
            </div>
          </div>
        </div>
      </body>
    </html>
  )
}
