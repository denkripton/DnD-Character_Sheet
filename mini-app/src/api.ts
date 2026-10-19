export type Character = {
  id: string
  name?: string | null
  kind: string
  spec_class: string
  alignment?: string | null
  background?: string | null
  level?: number | null
}

export type AuthSession = { access: string; user: { id: string; username: string } }

const baseUrl = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '') ?? ''

async function request<T>(path: string, token?: string): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!response.ok) {
    if (response.status === 401) throw new Error('Your session expired. Reopen this Mini App from Telegram.')
    throw new Error('The service could not complete this request. Try again shortly.')
  }
  return response.json() as Promise<T>
}

export function authenticate(initData: string): Promise<AuthSession> {
  return fetch(`${baseUrl}/users/auth/external`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ init_data: initData }),
  }).then(async response => {
    if (!response.ok) throw new Error(response.status === 401
      ? 'Telegram could not verify this session. Reopen the Mini App from your bot.'
      : 'Sign-in is temporarily unavailable. Try again shortly.')
    return response.json() as Promise<AuthSession>
  })
}

export function getCharacters(token: string): Promise<Character[]> {
  return request('/chatacters/my', token)
}

export function getCharacter(token: string, id: string): Promise<Character> {
  return request(`/chatacters/${encodeURIComponent(id)}`, token)
}
