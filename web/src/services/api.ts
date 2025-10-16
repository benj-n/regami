import { API_BASE } from '../env'

/**
 * API client using cookie-based authentication with CSRF protection.
 * All requests include credentials to send httpOnly cookies.
 * State-changing requests include X-CSRF-Token header for CSRF protection.
 * Token parameter kept for backward compatibility but not used.
 */

/**
 * Error response from API
 */
interface ApiErrorResponse {
  detail: string
  request_id?: string
  errors?: Array<{ field: string; message: string; type: string }>
}

/**
 * Get CSRF token from cookie.
 * The CSRF token is stored in a non-httpOnly cookie so JavaScript can read it.
 */
function getCsrfToken(): string | null {
  const match = document.cookie.match(/csrf_token=([^;]+)/)
  return match ? match[1] : null
}

/**
 * Extract user-friendly error message from API response.
 */
async function getErrorMessage(response: Response): Promise<string> {
  try {
    const data: ApiErrorResponse = await response.json()

    // If there's a detail message, use it
    if (data.detail) {
      return data.detail
    }

    // If there are validation errors, format them
    if (data.errors && data.errors.length > 0) {
      const errorMessages = data.errors.map(err => `${err.field}: ${err.message}`)
      return errorMessages.join(', ')
    }

    // Fallback to status text
    return response.statusText || 'An error occurred'
  } catch {
    // If response is not JSON, return status text
    return response.statusText || 'An error occurred'
  }
}

/**
 * Handle API response errors by throwing with user-friendly message.
 */
async function handleErrorResponse(response: Response): Promise<never> {
  const message = await getErrorMessage(response)
  throw new Error(message)
}

/**
 * Build headers for API requests.
 * Includes CSRF token for state-changing methods (POST, PUT, PATCH, DELETE).
 */
function buildHeaders(method: string, includeContentType: boolean = true): HeadersInit {
  const headers: HeadersInit = {}

  if (includeContentType) {
    headers['Content-Type'] = 'application/json'
  }

  // Add CSRF token for state-changing requests
  const stateMethods = ['POST', 'PUT', 'PATCH', 'DELETE']
  if (stateMethods.includes(method.toUpperCase())) {
    const csrfToken = getCsrfToken()
    if (csrfToken) {
      headers['X-CSRF-Token'] = csrfToken
    }
  }

  return headers
}

export async function apiGet<T>(path: string, token?: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: 'include', // Include cookies
  })
  if (!res.ok) await handleErrorResponse(res)
  return res.json()
}

export async function apiPost<T>(path: string, body: any, token?: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: buildHeaders('POST'),
    credentials: 'include',
    body: JSON.stringify(body),
  })
  if (!res.ok) await handleErrorResponse(res)
  return res.json()
}

export async function apiPut<T>(path: string, body: any, token?: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'PUT',
    headers: buildHeaders('PUT'),
    credentials: 'include',
    body: JSON.stringify(body),
  })
  if (!res.ok) await handleErrorResponse(res)
  return res.json()
}

export async function apiPutVoid(path: string, token?: string): Promise<void> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'PUT',
    headers: buildHeaders('PUT', false),
    credentials: 'include',
  })
  if (!res.ok) await handleErrorResponse(res)
}

export async function apiPostVoid(path: string, token?: string): Promise<void> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: buildHeaders('POST', false),
    credentials: 'include',
  })
  if (!res.ok) await handleErrorResponse(res)
}

export async function apiDeleteVoid(path: string, token?: string): Promise<void> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'DELETE',
    headers: buildHeaders('DELETE', false),
    credentials: 'include',
  })
  if (!res.ok) await handleErrorResponse(res)
}

export async function apiUpload<T>(path: string, formData: FormData, token?: string): Promise<T> {
  // For file uploads, we need to include CSRF token but not Content-Type
  // Browser will set Content-Type with multipart boundary
  const csrfToken = getCsrfToken()
  const headers: HeadersInit = {}
  if (csrfToken) {
    headers['X-CSRF-Token'] = csrfToken
  }

  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers,
    credentials: 'include',
    body: formData,
  })
  if (!res.ok) await handleErrorResponse(res)
  return res.json()
}
