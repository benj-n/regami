export const API_BASE = (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:8000'

export function toIso(value: string): string {
  // datetime-local is local time; convert to ISO string assuming local timezone
  if (!value) return ''
  const d = new Date(value)
  return d.toISOString()
}
