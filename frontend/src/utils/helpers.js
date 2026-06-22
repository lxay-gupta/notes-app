import { formatDistanceToNow, format } from 'date-fns'

export const fmtRelative = (dateStr) => {
  try {
    return formatDistanceToNow(new Date(dateStr), { addSuffix: true })
  } catch {
    return dateStr
  }
}

export const fmtDate = (dateStr) => {
  try {
    return format(new Date(dateStr), 'MMM d, yyyy')
  } catch {
    return dateStr
  }
}

export const fmtDateTime = (dateStr) => {
  try {
    return format(new Date(dateStr), 'MMM d, yyyy · h:mm a')
  } catch {
    return dateStr
  }
}

/** Extract a human-readable message from an Axios error response. */
export const extractError = (err) => {
  const detail = err?.response?.data?.detail
  if (!detail) return err?.message ?? 'Something went wrong.'
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map(d => d.msg).join('; ')
  return JSON.stringify(detail)
}

/** Truncate text to a maximum character count with an ellipsis. */
export const truncate = (str, max = 120) =>
  str && str.length > max ? str.slice(0, max).trimEnd() + '…' : str
