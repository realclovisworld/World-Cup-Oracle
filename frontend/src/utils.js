// Date formatting helpers (IMPLEMENTATION_FIFA §6).

export function formatMatchDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr + 'T00:00:00')
  return d.toLocaleDateString('en-GB', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
}

// FIFA style: "04/07/2026 20:00" (time optional).
export function formatMatchDateTime(dateStr, timeStr) {
  if (!dateStr) return 'Predicted'
  const formatted = formatMatchDate(dateStr)
  return timeStr ? `${formatted} ${timeStr}` : formatted
}
