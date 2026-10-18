// 14341 -> '9d 23h', 135 -> '2h 15m', 42 -> '42m'
export const formatDuration = (minutes) => {
  const total = Math.max(0, Math.round(Number(minutes) || 0))
  const days = Math.floor(total / 1440)
  const hours = Math.floor((total % 1440) / 60)
  const mins = total % 60
  if (days > 0) return `${days}d ${hours}h`
  if (hours > 0) return `${hours}h ${mins}m`
  return `${mins}m`
}
