import { useState, useEffect } from 'react'
import { getJobResult } from '../api/jobs'

const PAGE_SIZE = 100

export function ResultTable({ jobId }) {
  const [data, setData] = useState(null)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!jobId) return
    setLoading(true)
    setError(null)
    getJobResult(jobId, page, PAGE_SIZE)
      .then(setData)
      .catch((err) => setError(err.response?.data?.error || 'Failed to load results'))
      .finally(() => setLoading(false))
  }, [jobId, page])

  const handleDownload = () => {
    window.open(`/api/v1/jobs/${jobId}/download/`, '_blank')
  }

  if (!jobId) return null
  if (loading) return <div className="loading">Loading results…</div>
  if (error) return <div className="error">{error}</div>
  if (!data) return null

  const totalPages = data.total_rows ? Math.ceil(data.total_rows / PAGE_SIZE) : 1

  return (
    <div className="result-table-wrapper">
      <div className="result-toolbar">
        <div className="result-meta">
          Showing rows {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, data.total_rows)} of{' '}
          {Number(data.total_rows).toLocaleString()} total
        </div>
        <button className="download-btn" onClick={handleDownload}>
          ↓ Download CSV
        </button>
      </div>

      <div className="table-scroll">
        <table className="result-table">
          <thead>
            <tr>{data.headers.map(h => <th key={h}>{h}</th>)}</tr>
          </thead>
          <tbody>
            {data.rows.map((row, i) => (
              <tr key={i}>
                {data.headers.map(h => <td key={h}>{row[h]}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="pagination">
        <button onClick={() => setPage(1)} disabled={page === 1}>«</button>
        <button onClick={() => setPage(p => p - 1)} disabled={page === 1}>‹</button>
        <span>Page {page} of {totalPages}</span>
        <button onClick={() => setPage(p => p + 1)} disabled={page >= totalPages}>›</button>
        <button onClick={() => setPage(totalPages)} disabled={page >= totalPages}>»</button>
      </div>
    </div>
  )
}
