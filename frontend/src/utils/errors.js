export const getErrorMessage = (err, fallback) => {
  const detail = err?.response?.data?.detail
  return typeof detail === 'string' && detail ? detail : fallback
}
