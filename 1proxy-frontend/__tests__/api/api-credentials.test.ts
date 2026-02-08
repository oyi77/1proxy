import { describe, it, expect, beforeEach, vi } from 'vitest'
import { api } from '@/lib/api'

describe('api fetch credentials', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('includes credentials for admin endpoints', async () => {
    const fetchMock = global.fetch as unknown as ReturnType<typeof vi.fn>
    fetchMock.mockResolvedValue({ ok: true, json: async () => ({}) } as any)

    await api.getAdminValidationStats()

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/admin/validation-stats'),
      expect.objectContaining({ credentials: 'include' })
    )
  })

  it('includes credentials for mutating endpoints', async () => {
    const fetchMock = global.fetch as unknown as ReturnType<typeof vi.fn>
    fetchMock.mockResolvedValue({ ok: true, json: async () => ({}) } as any)

    await api.deleteProxy(123)

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/proxies/123'),
      expect.objectContaining({ method: 'DELETE', credentials: 'include' })
    )
  })
})
