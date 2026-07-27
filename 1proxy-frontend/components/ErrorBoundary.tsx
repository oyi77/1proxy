'use client';

import { Component, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div className="p-8 text-center">
          <h2 className="text-xl font-bold mb-2" style={{ fontFamily: "'Press Start 2P','Courier New',monospace", fontSize: '0.75rem' }}>
            ⚠️ Something went wrong
          </h2>
          <p className="text-sm mb-4" style={{ fontFamily: "'Courier New',monospace", color: '#666' }}>
            {this.state.error?.message || 'An unexpected error occurred'}
          </p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 rounded-lg font-bold"
            style={{
              backgroundColor: 'var(--retro-pink)',
              color: '#FFFFFF',
              border: '2px solid #000000',
              fontFamily: "'Press Start 2P','Courier New',monospace",
              fontSize: '0.65rem',
              cursor: 'pointer',
            }}
          >
            Reload Page
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
