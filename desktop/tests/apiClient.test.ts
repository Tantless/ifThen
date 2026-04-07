import { describe, expect, it, vi } from 'vitest'

import { createApiClient } from '../src/lib/apiClient'

describe('createApiClient', () => {
  it('prefixes paths with the local api origin', async () => {
    const fetchMock = vi.fn(async () => ({
      ok: true,
      status: 200,
      json: async () => [],
    }))

    await createApiClient(fetchMock as unknown as typeof fetch).get('/conversations')

    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/conversations',
      expect.objectContaining({ method: 'GET' }),
    )
  })

  it('returns undefined for 204 responses', async () => {
    const fetchMock = vi.fn(async () => ({
      ok: true,
      status: 204,
    }))

    await expect(createApiClient(fetchMock as unknown as typeof fetch).delete('/conversations/1')).resolves.toBeUndefined()
  })

  it('throws for non-2xx responses', async () => {
    const fetchMock = vi.fn(async () => ({
      ok: false,
      status: 500,
      text: async () => 'boom',
    }))

    await expect(createApiClient(fetchMock as unknown as typeof fetch).get('/conversations')).rejects.toThrow(
      'API request failed: 500 boom',
    )
  })
})
