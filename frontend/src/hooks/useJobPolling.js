/**
 * useJobPolling.js
 *
 * Polls GET /jobs/{jobId}/ every 2 seconds while a job is active.
 * Stops automatically when the job reaches SUCCESS, FAILED, or CANCELLED.
 *
 * Usage:
 *   const { job, error } = useJobPolling(jobId)
 */

import { useState, useEffect, useRef } from 'react'
import { getJobStatus } from '../api/jobs'

const POLL_INTERVAL_MS = 2000
const TERMINAL_STATES = ['SUCCESS', 'FAILED', 'CANCELLED']

export function useJobPolling(jobId) {
  const [job, setJob] = useState(null)
  const [error, setError] = useState(null)
  const intervalRef = useRef(null)

  useEffect(() => {
    // Clear any existing interval when jobId changes
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
    }

    if (!jobId) {
      setJob(null)
      setError(null)
      return
    }

    // Poll immediately on mount, then every 2 seconds
    const poll = async () => {
      try {
        const data = await getJobStatus(jobId)
        setJob(data)
        setError(null)

        // Stop polling when job is done
        if (TERMINAL_STATES.includes(data.status)) {
          clearInterval(intervalRef.current)
        }
      } catch (err) {
        setError(err.response?.data?.error || 'Failed to fetch job status')
      }
    }

    poll()
    intervalRef.current = setInterval(poll, POLL_INTERVAL_MS)

    return () => clearInterval(intervalRef.current)
  }, [jobId])

  return { job, error }
}
