import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import './App.css'

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

type ProgressEvent = {
  stage: string
  progress: number
  message: string
  warning?: string
  error?: string
}

function App() {
  const [claim, setClaim] = useState('')
  const [files, setFiles] = useState<File[]>([])
  const [progress, setProgress] = useState<ProgressEvent | null>(null)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const sourceRef = useRef<EventSource | null>(null)

  useEffect(() => () => sourceRef.current?.close(), [])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setProgress(null)
    setSubmitting(true)
    sourceRef.current?.close()

    const body = new FormData()
    body.append('claim', claim)
    files.forEach((file) => body.append('files', file))

    try {
      const response = await fetch(`${API_BASE}/api/analyses`, { method: 'POST', body })
      if (!response.ok) {
        const payload = await response.json().catch(() => null)
        throw new Error(payload?.detail ?? 'Could not start analysis.')
      }
      const { analysis_id: analysisId } = await response.json()
      const source = new EventSource(`${API_BASE}/api/analyses/${analysisId}/events`)
      sourceRef.current = source

      const update = (message: MessageEvent<string>) => {
        const next = JSON.parse(message.data) as ProgressEvent
        setProgress(next)
        if (next.stage === 'COMPLETED' || next.stage === 'COMPLETED_WITH_WARNINGS' || next.stage === 'FAILED') {
          setSubmitting(false)
          source.close()
        }
      }

      source.addEventListener('progress', update)
      source.addEventListener('completed', update)
      source.addEventListener('completed_with_warnings', update)
      source.addEventListener('failed', update)
      source.onerror = () => {
        setError('Progress connection was interrupted.')
        setSubmitting(false)
        source.close()
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not start analysis.')
      setSubmitting(false)
    }
  }

  return (
    <main>
      <section className="panel">
        <p className="eyebrow">EvidenceSplit</p>
        <h1>Compare scientific evidence</h1>
        <form onSubmit={submit}>
          <label htmlFor="claim">Scientific claim</label>
          <textarea
            id="claim"
            value={claim}
            onChange={(event) => setClaim(event.target.value)}
            placeholder="Enter the exact claim to analyze"
            required
          />
          <label htmlFor="files">Research PDFs</label>
          <small>Select several at once or add them in multiple batches (maximum 5).</small>
          <input
            id="files"
            type="file"
            accept="application/pdf,.pdf"
            multiple
            onChange={(event) => {
              const selected = Array.from(event.target.files ?? [])
              setFiles((current) => {
                const combined = [...current, ...selected]
                return combined
                  .filter(
                    (file, index) =>
                      combined.findIndex(
                        (candidate) =>
                          candidate.name === file.name &&
                          candidate.size === file.size &&
                          candidate.lastModified === file.lastModified,
                      ) === index,
                  )
                  .slice(0, 5)
              })
              event.target.value = ''
            }}
          />
          {files.length > 0 && (
            <ul className="file-list">
              {files.map((file) => (
                <li key={`${file.name}-${file.size}-${file.lastModified}`}>
                  <span>{file.name}</span>
                  <button
                    type="button"
                    onClick={() => setFiles((current) => current.filter((candidate) => candidate !== file))}
                  >
                    Remove
                  </button>
                </li>
              ))}
            </ul>
          )}
          <button disabled={submitting || !claim.trim()}>{submitting ? 'Analyzing…' : 'Analyze evidence'}</button>
        </form>

        {progress && (
          <section className="progress" aria-live="polite">
            <div><strong>{progress.message}</strong><span>{progress.progress}%</span></div>
            <progress value={progress.progress} max="100" />
            {progress.warning && <p className="warning">{progress.warning}</p>}
            {progress.error && <p className="error">{progress.error}</p>}
          </section>
        )}
        {error && <p className="error" role="alert">{error}</p>}
      </section>
    </main>
  )
}

export default App
