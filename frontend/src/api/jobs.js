import axios from 'axios'

// In production, API calls go to the Django backend URL directly.
// In development, Vite proxy handles /api/* → http://web:8000
const BASE_URL = import.meta.env.VITE_API_BASE_URL
  ? `${import.meta.env.VITE_API_BASE_URL}/api/v1`
  : '/api/v1'

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
})

export async function createJob({ file, nlPrompt, targetColumns, replacementValue }) {
  const formData = new FormData()
  formData.append('upload_file', file)
  formData.append('original_filename', file.name)
  formData.append('nl_prompt', nlPrompt)
  formData.append('target_columns', targetColumns)
  formData.append('replacement_value', replacementValue)

  const res = await api.post('/jobs/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}

export async function getJobStatus(jobId) {
  const res = await api.get(`/jobs/${jobId}/`)
  return res.data
}

export async function getJobResult(jobId, page = 1, pageSize = 100) {
  const res = await api.get(`/jobs/${jobId}/result/`, {
    params: { page, page_size: pageSize },
  })
  return res.data
}

export async function cancelJob(jobId) {
  const res = await api.post(`/jobs/${jobId}/cancel/`)
  return res.data
}

export async function listJobs() {
  const res = await api.get('/jobs/')
  return res.data
}

export async function deleteJob(jobId) {
  await api.delete(`/jobs/${jobId}/delete/`)
}

export async function clearFailedJobs() {
  const res = await api.delete('/jobs/bulk-delete/', { params: { status: 'FAILED' } })
  return res.data
}

export function getDownloadUrl(jobId) {
  return `${BASE_URL}/jobs/${jobId}/download/`
}
