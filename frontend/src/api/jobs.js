/**
 * api/jobs.js — all HTTP calls to the Django backend.
 *
 * Keeping every API call here means if the backend URL changes,
 * you fix it in one place, not scattered across components.
 */

import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

/**
 * Upload a file and create a job.
 * Returns { job_id, status }
 */
export async function createJob({ file, nlPrompt, targetColumns, replacementValue }) {
  const formData = new FormData()
  formData.append('upload_file', file)
  formData.append('original_filename', file.name)
  formData.append('nl_prompt', nlPrompt)
  formData.append('target_columns', targetColumns)   // comma-separated string
  formData.append('replacement_value', replacementValue)

  const res = await api.post('/jobs/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}

/**
 * Poll job status. Returns full job object including status + progress.
 */
export async function getJobStatus(jobId) {
  const res = await api.get(`/jobs/${jobId}/`)
  return res.data
}

/**
 * Fetch a page of results for a completed job.
 */
export async function getJobResult(jobId, page = 1, pageSize = 100) {
  const res = await api.get(`/jobs/${jobId}/result/`, {
    params: { page, page_size: pageSize },
  })
  return res.data
}

/**
 * Cancel a running job.
 */
export async function cancelJob(jobId) {
  const res = await api.post(`/jobs/${jobId}/cancel/`)
  return res.data
}

/**
 * List all jobs.
 */
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

export async function listFiles() {
  const res = await api.get('/files/')
  return res.data
}

export async function createJobFromFile({ filePath, nlPrompt, targetColumns, replacementValue }) {
  const res = await api.post('/jobs/from-file/', {
    file_path: filePath,
    nl_prompt: nlPrompt,
    target_columns: targetColumns,
    replacement_value: replacementValue,
  })
  return res.data
}
