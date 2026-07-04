import { useState } from 'react'
import { UploadForm } from './components/UploadForm'
import { JobStatus } from './components/JobStatus'
import { ResultTable } from './components/ResultTable'
import { JobHistory } from './components/JobHistory'
import { useJobPolling } from './hooks/useJobPolling'

export default function App() {
  const [stage, setStage] = useState('idle')
  const [jobId, setJobId] = useState(null)

  const { job, error: pollError } = useJobPolling(
    stage === 'polling' || stage === 'complete' ? jobId : null
  )

  if (stage === 'polling' && job?.status === 'SUCCESS') {
    setStage('complete')
  }

  const handleJobCreated = (id) => { setJobId(id); setStage('polling') }
  const handleReset = () => { setJobId(null); setStage('idle') }

  // Load a historical job directly into results view
  const handleSelectHistoryJob = (id) => {
    setJobId(id)
    setStage('complete')
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="logo">◆ Rhombus AI</div>
        <p className="tagline">Natural Language → Regex → Data Transformation at Scale</p>
      </header>

      <main className="app-main">
        {stage === 'idle' && (
          <>
            <UploadForm onJobCreated={handleJobCreated} />
            <JobHistory onSelectJob={handleSelectHistoryJob} />
          </>
        )}

        {(stage === 'polling' || stage === 'complete') && (
          <>
            {pollError && <div className="error">{pollError}</div>}
            <JobStatus job={job} onCancel={handleReset} />
            {stage === 'complete' && <ResultTable jobId={jobId} />}
            {job && ['SUCCESS', 'FAILED', 'CANCELLED'].includes(job.status) && (
              <button className="new-job-btn" onClick={handleReset}>＋ New Job</button>
            )}
          </>
        )}
      </main>
    </div>
  )
}
