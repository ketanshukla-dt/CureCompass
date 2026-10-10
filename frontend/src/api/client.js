import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export const fetchIncidents      = ()   => api.get('/incidents').then(r => r.data)
export const fetchIncident       = (id) => api.get(`/incidents/${id}`).then(r => r.data)
export const analyzeIncident     = (id) => api.post(`/incidents/${id}/analyze`).then(r => r.data)
export const resolveIncident     = (id, body) => api.post(`/incidents/${id}/resolve`, body).then(r => r.data)
export const validateResolution  = (id) => api.post(`/incidents/${id}/validate`).then(r => r.data)
export const fetchHistory        = ()   => api.get('/history').then(r => r.data)
export const fetchHistoryStats   = ()   => api.get('/history/stats').then(r => r.data)
