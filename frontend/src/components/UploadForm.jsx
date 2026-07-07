import { useState } from 'react'
import { createJob } from '../api/jobs'

async function previewColumns(file) {
  return new Promise((resolve) => {
    const ext = file.name.split('.').pop().toLowerCase()
    if (ext !== 'csv') { resolve([]); return }
    const reader = new FileReader()
    reader.onload = (e) => {
      const firstLine = e.target.result.split('\n')[0]
      const cols = firstLine.split(',').map(c => c.trim().replace(/^"|"$/g, ''))
      resolve(cols)
    }
    reader.readAsText(file.slice(0, 4096))
  })
}

export function UploadForm({ onJobCreated }) {
  const [file, setFile] = useState(null)
  const [columns, setColumns] = useState([])
  const [nlPrompt, setNlPrompt] = useState('')
  const [targetColumns, setTargetColumns] = useState('')
  const [replacementValue, setReplacementValue] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleFileChange = async (e) => {
    const f = e.target.files[0]
    if (!f) return
    setFile(f)
    setError(null)
    const cols = await previewColumns(f)
    setColumns(cols)
  }

  const handleColumnClick = (col) => {
    setTargetColumns(prev => {
      if (!prev.trim()) return col
      const existing = prev.split(',').map(c => c.trim())
      if (existing.includes(col)) return prev
      return prev + ', ' + col
    })
  }

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

      <div className="field">
        <label>CSV or Excel File</label>
        <input type="file" accept=".csv,.xlsx,.xls" onChange={handleFileChange} />
        {file && (
          <span className="hint">{file.name} — {(file.size / 1024 / 1024).toFixed(2)} MB</span>
        )}
      </div>

      <div className="field">
        <label>Describe what to find</label>
        <textarea
          rows={3}
          placeholder='e.g. "Find all email addresses" or "Match phone numbers"'
          value={nlPrompt}
          onChange={(e) => setNlPrompt(e.target.value)}
        />
      </div>

      <div className="field">
        <label>Target column(s)</label>
        {columns.length > 0 && (
          <div className="column-chips">
            {columns.map(col => (
              <button
                key={col}
                type="button"
                className="column-chip"
                onClick={() => handleColumnClick(col)}
              >
                {col}
              </button>
            ))}
          </div>
        )}
        <input
          type="text"
          placeholder={columns.length > 0 ? 'Click above or type here' : 'e.g. Email  or  Email, Notes'}
          value={targetColumns}
          onChange={(e) => setTargetColumns(e.target.value)}
        />
        <span className="hint">Comma-separated for multiple columns.</span>
      </div>

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
