import { useState, useEffect } from 'react'
import { listJobs, deleteJob, clearFailedJobs } from '../api/jobs'

const STATUS_COLOURS = {
  QUEUED:    '#6b7280',
  RUNNING:   '#3b82f6',
  SUCCESS:   '#22c55e',
  FAILED:    '#ef4444',
  CANCELLED: '#f59e0b',
}

function timeAgo(dateStr) {
  const diff = Math.floor((Date.now() - new Date(dateStr)) / 1000)
  if (diff < 60) return `${diff}s ago`
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}

export function JobHistory({ onSelectJob }) {
  const [jobs, setJobs] = useState([])
  const [open, setOpen] = useState(false)

  const load = () => listJobs().then(setJobs).catch(() => {})

  useEffect(() => { if (open) load() }, [open])

  const handleDelete = async (e, jobId) => {
    e.stopPropagation()
    await deleteJob(jobId)
    setJobs(prev => prev.filter(j => j.id !== jobId))
  }

  const handleClearFailed = async () => {
    await clearFailedJobs()
    setJobs(prev => prev.filter(j => j.status !== 'FAILED'))
  }

  const hasFailed = jobs.some(j => j.status === 'FAILED')

  return (
    <div className="history-wrapper">
      <button className="history-toggle" onClick={() => setOpen(o => !o)}>
        {open ? '▲ Hide history' : '▼ View past jobs'}
      </button>

      {open && (
        <div className="history-panel">
          {hasFailed && (
            <div className="history-toolbar">
              <button className="clear-failed-btn" onClick={handleClearFailed}>
                🗑 Clear all failed
              </button>
            </div>
          )}

          {jobs.length === 0 && (
            <div className="history-empty">No past jobs found.</div>
          )}

          {jobs.map(job => (
            <div
              key={job.id}
              className="history-row"
              onClick={() => job.status === 'SUCCESS' ? onSelectJob(job.id) : null}
              style={{ cursor: job.status === 'SUCCESS' ? 'pointer' : 'default' }}
            >
              <div className="history-main">
                <span className="history-dot"
                  style={{ backgroundColor: STATUS_COLOURS[job.status] || '#6b7280' }}
                />
                <span className="history-filename">{job.original_filename}</span>
                <span className="history-prompt">"{job.nl_prompt}"</span>
              </div>
              <div className="history-meta">
                <span className="history-status">{job.status}</span>
                <span className="history-time">{timeAgo(job.created_at)}</span>
                <button
                  className="history-delete-btn"
                  onClick={(e) => handleDelete(e, job.id)}
                  title="Delete this job"
                >✕</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
