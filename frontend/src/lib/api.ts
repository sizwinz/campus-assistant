import type { ChatResponse, DashboardStats } from './types'

const API_BASE_URL =
  (process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000').replace(
    /\/$/,
    ''
  )

async function buildApiError(response: Response): Promise<Error> {
  let detail = response.statusText

  try {
    const body = await response.json()
    if (typeof body?.detail === 'string') {
      detail = body.detail
    } else if (body?.detail) {
      detail = JSON.stringify(body.detail)
    }
  } catch {
    // Keep statusText when the backend does not return JSON.
  }

  return new Error(`API error ${response.status}: ${detail}`)
}

export const chatApi = {
  async sendMessage(
    message: string,
    sessionId?: string,
    language?: string
  ): Promise<ChatResponse> {
    const response = await fetch(`${API_BASE_URL}/api/v1/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message,
        session_id: sessionId,
        language,
      }),
    })

    if (!response.ok) {
      throw await buildApiError(response)
    }

    return response.json()
  },
}

export const adminApi = {
  async getDashboard(username: string, password: string): Promise<DashboardStats> {
    const credentials = btoa(`${username}:${password}`)
    const response = await fetch(`${API_BASE_URL}/api/v1/admin/dashboard`, {
      method: 'GET',
      headers: {
        Authorization: `Basic ${credentials}`,
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      throw await buildApiError(response)
    }

    return response.json()
  },
}
