'use client'

import { useEffect } from 'react'

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    // Log the error to an error reporting service
    console.error('Application error:', error)
  }, [error])

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-retro-dark via-retro-blue to-retro-purple">
      <div className="max-w-md w-full mx-4 p-8 bg-retro-dark border-4 border-retro-cyan rounded-lg shadow-[0_0_30px_rgba(0,255,255,0.3)]">
        <div className="text-center">
          {/* Retro-style error icon */}
          <div className="mb-6 text-6xl text-retro-pink">⚠️</div>
          
          <h2 className="text-2xl font-bold text-retro-cyan mb-4 font-retro">
            SYSTEM ERROR
          </h2>
          
          <p className="text-retro-text mb-6">
            Something went wrong! The proxy matrix encountered an unexpected error.
          </p>
          
          {error.message && (
            <div className="mb-6 p-4 bg-black/30 border border-retro-pink/30 rounded">
              <p className="text-sm text-retro-pink font-mono break-words">
                {error.message}
              </p>
            </div>
          )}
          
          <div className="flex flex-col gap-3">
            <button
              onClick={() => reset()}
              className="w-full px-6 py-3 bg-retro-cyan text-retro-dark font-bold rounded 
                       hover:bg-retro-cyan/80 transition-all transform hover:scale-105
                       shadow-[0_0_20px_rgba(0,255,255,0.5)]"
            >
              TRY AGAIN
            </button>
            
            <button
              onClick={() => window.location.href = '/'}
              className="w-full px-6 py-3 bg-retro-purple text-white font-bold rounded 
                       hover:bg-retro-purple/80 transition-all
                       border-2 border-retro-purple"
            >
              GO TO HOME
            </button>
          </div>
          
          {error.digest && (
            <p className="mt-4 text-xs text-retro-text/50 font-mono">
              Error ID: {error.digest}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
