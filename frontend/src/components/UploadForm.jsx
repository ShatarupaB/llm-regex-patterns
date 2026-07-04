/**
 * UploadForm.jsx
 *
 * Collects: CSV/Excel file, natural-language prompt,
 * target column(s), and replacement value.
 * On submit → calls createJob() → passes job_id up to App.
 */

import { useState } from 'react'
import { createJob } from '../api/jobs'

export function UploadForm({ onJobCreated }) {
  const [file, setFile] = useState(null)
  const [nlPrompt, setNlPrompt] = useState('')
  const [targetColumns, setTargetColumns] = useState('')
  const [replacementValue, setReplacementValue] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)

    if (!file) return setError('Please select a file.')
    if (!nlPrompt.trim()) return setError('Please describe the pattern.')
    if (!targetColumns.trim()) return setError('Please enter at least one column name.')
    if (!replacementValue.trim()) return setError('Please enter a replacement value.')

    setLoading(true)
    try {
      const result = await createJob({ file, nlPrompt, targetColumns, replacementValue })
      onJobCreated(result.job_id)
    } catch (err) {
      setError(err.response?.data?.detail || JSON.stringify(err.response?.data) || 'Upload failed.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="upload-form">
      <h2>New Job</h2>

      {/* File upload */}
      <div className="field">
        <label>CSV or Excel File</label>
        <input
          type="file"
          accept=".csv,.xlsx,.xls"
          onChange={(e) => setFile(e.target.files[0])}
        />
        {file && <span className="hint">{file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB)</span>}
      </div>

      {/* Natural language prompt */}
      <div className="field">
        <label>Describe what to find</label>
        <textarea
          rows={3}
          placeholder='e.g. "Find all email addresses" or "Match phone numbers in US format"'
          value={nlPrompt}
          onChange={(e) => setNlPrompt(e.target.value)}
        />
      </div>

      {/* Target columns */}
      <div className="field">
        <label>Target column(s)</label>
        <input
          type="text"
          placeholder="e.g. Email  or  Email, Notes, Description"
          value={targetColumns}
          onChange={(e) => setTargetColumns(e.target.value)}
        />
        <span className="hint">Comma-separated if multiple columns</span>
      </div>

      {/* Replacement value */}
      <div className="field">
        <label>Replace matches with</label>
        <input
          type="text"
          placeholder='e.g. REDACTED'
          value={replacementValue}
          onChange={(e) => setReplacementValue(e.target.value)}
        />
      </div>

      {error && <div className="error">{error}</div>}

      <button type="submit" disabled={loading}>
        {loading ? 'Uploading...' : 'Run Job'}
      </button>
    </form>
  )
}
