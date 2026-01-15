import { render, screen } from '@testing-library/react'
import { ProxyTable } from '@/components/ProxyTable'
import { describe, it, expect, vi } from 'vitest'

const mockProxies = [
  {
    id: 1,
    url: 'http://1.1.1.1:8080',
    protocol: 'http',
    ip: '1.1.1.1',
    port: 8080,
    country_code: 'US',
    country_name: 'United States',
    latency_ms: 100,
    quality_score: 90,
    anonymity: 'Elite',
    is_working: true,
    created_at: new Date().toISOString()
  }
]

describe('ProxyTable', () => {
  it('renders loading state', () => {
    render(
      <ProxyTable 
        proxies={[]} 
        loading={true} 
        total={0} 
        limit={10} 
        currentPage={0} 
        onPageChange={() => {}} 
      />
    )
    expect(screen.getByText(/Loading proxies/i)).toBeInTheDocument()
  })

  it('renders proxy data', () => {
    render(
      <ProxyTable 
        proxies={mockProxies} 
        loading={false} 
        total={1} 
        limit={10} 
        currentPage={0} 
        onPageChange={() => {}} 
      />
    )
    expect(screen.getByText('1.1.1.1:8080')).toBeInTheDocument()
    expect(screen.getByText('HTTP')).toBeInTheDocument()
    expect(screen.getByText('Elite')).toBeInTheDocument()
    expect(screen.getByText('100ms')).toBeInTheDocument()
  })

  it('renders empty state when no proxies', () => {
    render(
      <ProxyTable 
        proxies={[]} 
        loading={false} 
        total={0} 
        limit={10} 
        currentPage={0} 
        onPageChange={() => {}} 
      />
    )
    expect(screen.getByText(/No proxies found/i)).toBeInTheDocument()
  })
})
