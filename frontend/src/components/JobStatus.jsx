import { cancelJob } from '../api/jobs'

const STATUS_COLOURS = {
  QUEUED:    '#6b7280',
  RUNNING:   '#3b82f6',
  SUCCESS:   '#22c55e',
  FAILED:    '#ef4444',
  CANCELLED: '#f59e0b',
}

const STATUS_LABELS = {
  QUEUED:    'Queued',
  RUNNING:   'Running',
  SUCCESS:   'Complete',
  FAILED:    'Failed',
  CANCELLED: 'Cancelled',
}

function parseErrorMessage(raw) {
  if (!raw) return 'An unexpected error occurred.'
  const match = raw.match(/(?:RuntimeError|ValueError|Exception):\s*(.+?)(?:\n|$)/s)
  if (match) return match[1].trim()
  const lines = raw.split('\n').map(l => l.trim()).filter(Boolean)
  return lines[lines.length - 1] || 'An unexpected error occurred.'
}

export function JobStatus({ job, onCancel }) {
  if (!job) return null

  const colour = STATUS_COLOURS[job.status] || '#6b7280'
  const isActive = job.status === 'QUEUED' || job.status === 'RUNNING'

  const handleCancel = async () => {
    if (!window.confirm('Cancel this job?')) return
    try {
      await cancelJob(job.id)
      // Wait for next poll to pick up CANCELLED status before resetting UI
      setTimeout(() => onCancel?.(), 2000)
    } catch (err) {
      alert('Failed to cancel: ' + (err.response?.data?.error || err.message))
    }
  }

  return (
    <div className="job-status">
      <div className="status-header">
        <span className="status-badge" style={{ backgroundColor: colour }}>
          {STATUS_LABELS[job.status] || job.status}
        </span>
        <span className="job-id">Job {job.id.slice(0, 8)}…</span>
        {isActive && (
          <button className="cancel-btn" onClick={handleCancel}>Cancel</button>
        )}
      </div>

      {job.status !== 'SUCCESS' && (
        <>
          <div className="progress-track">
            <div className="progress-fill"
              style={{ width: `${job.progress}%`, backgroundColor: colour, transition: 'width 0.4s ease' }}
            />
          </div>
          <div className="progress-label">{job.progress}%</div>
        </>
      )}

      {isActive && job.celery_meta?.message && (
        <div className="status-message">{job.celery_meta.message}</div>
      )}

      {job.status === 'SUCCESS' && (
        <div className="success-summary">
          ✅ {Number(job.result_row_count).toLocaleString()} rows processed successfully
        </div>
      )}

      {job.status === 'CANCELLED' && (
        <div className="status-message">Job was cancelled.</div>
      )}

      {job.status === 'FAILED' && (
        <div className="error-block">
          <div className="error-title">⚠️ Job failed</div>
          <div className="error-body">{parseErrorMessage(job.error_message)}</div>
        </div>
      )}
    </div>
  )
}
