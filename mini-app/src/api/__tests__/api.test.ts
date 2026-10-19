import { afterEach, describe, expect, it, vi } from 'vitest'
import { authenticate, getCharacters } from '../../api'

afterEach(() => vi.unstubAllGlobals())

describe('Mini App API', () => {
  it('submits raw initData for trusted backend verification', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ access: 'jwt' }) })
    vi.stubGlobal('fetch', fetchMock)

    await authenticate('signed-query')

    expect(fetchMock.mock.calls[0][0]).toContain('/users/auth/external')
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ init_data: 'signed-query' })
    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBeUndefined()
  })

  it('surfaces unauthorized character requests as expired sessions', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 401 }))

    await expect(getCharacters('token')).rejects.toThrow('Your session expired')
  })
})
