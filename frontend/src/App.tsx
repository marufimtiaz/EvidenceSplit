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

type Finding = {
  id: string
  evidence_quote: string
  explanation: string
  conditions: string | null
  confidence: number
  page_start: number | null
  page_end: number | null
}

type EvidenceCard = {
  document_id: string
  title: string
  authors: string[]
  year: number | null
  doi: string | null
  source_url: string | null
  source_type: 'UPLOADED_PDF' | 'LIVE_FULL_TEXT' | 'LIVE_ABSTRACT'
  paper_stance: 'SUPPORTING' | 'CONTRADICTING' | 'QUALIFYING'
  paper_summary: string
  findings: Finding[]
}

type AnalysisResult = {
  id: string
  claim: string
  status: string
  warning_message: string | null
  error_message: string | null
  overall_assessment: string | null
  summary: string | null
  retrieved_paper_count: number
  supporting: EvidenceCard[]
  contradicting: EvidenceCard[]
  qualifying: EvidenceCard[]
  limitations: string[]
}

type DemoConfig = {
  enabled: boolean
  claims: string[]
}

const sourceLabels = {
  UPLOADED_PDF: 'Uploaded full text',
  LIVE_FULL_TEXT: 'Live full text',
  LIVE_ABSTRACT: 'Abstract only',
}

function EvidenceCardView({ card }: { card: EvidenceCard }) {
  const sourceHref = card.doi
    ? `https://doi.org/${card.doi.replace(/^https?:\/\/(dx\.)?doi\.org\//, '')}`
    : card.source_url

  return (
    <article className={`evidence-card ${card.source_type === 'LIVE_ABSTRACT' ? 'abstract-only' : ''}`}>
      <div className="card-badges">
        <span className={`source-badge ${card.source_type.toLowerCase()}`}>{sourceLabels[card.source_type]}</span>
        <span className="stance-badge">{card.paper_stance}</span>
      </div>
      <h3>{card.title}</h3>
      <p className="metadata">
        {card.authors.length ? card.authors.join(', ') : 'Authors unavailable'}
        {card.year ? ` · ${card.year}` : ''}
      </p>
      <p>{card.paper_summary}</p>
      {card.findings.map((finding) => (
        <details key={finding.id}>
          <summary>View evidence quote</summary>
          <blockquote>{finding.evidence_quote}</blockquote>
          <p>{finding.explanation}</p>
          {finding.conditions && <p><strong>Conditions:</strong> {finding.conditions}</p>}
          {finding.page_start && (
            <p className="metadata">
              Page {finding.page_start}{finding.page_end !== finding.page_start ? `–${finding.page_end}` : ''}
            </p>
          )}
          <p className="citation-id">Citation: <code>{finding.id}</code></p>
        </details>
      ))}
      {sourceHref && <a className="source-link" href={sourceHref} target="_blank" rel="noreferrer">Open source ↗</a>}
    </article>
  )
}

function App() {
  const [claim, setClaim] = useState('')
  const [files, setFiles] = useState<File[]>([])
  const [progress, setProgress] = useState<ProgressEvent | null>(null)
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [demoClaims, setDemoClaims] = useState<string[]>([])
  const sourceRef = useRef<EventSource | null>(null)

  useEffect(() => {
    void fetch(`${API_BASE}/api/analyses/demo-claims`)
      .then((response) => response.ok ? response.json() as Promise<DemoConfig> : null)
      .then((config) => {
        if (config?.enabled && config.claims.length) {
          setDemoClaims(config.claims)
          setClaim(config.claims[0])
          setFiles([])
        }
      })
      .catch(() => undefined)
    return () => sourceRef.current?.close()
  }, [])

  async function loadResult(analysisId: string) {
    const response = await fetch(`${API_BASE}/api/analyses/${analysisId}`)
    if (!response.ok) throw new Error('Could not load the analysis result.')
    setResult(await response.json() as AnalysisResult)
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setProgress(null)
    setResult(null)
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
        if (['COMPLETED', 'COMPLETED_WITH_WARNINGS', 'FAILED'].includes(next.stage)) {
          setSubmitting(false)
          source.close()
          void loadResult(analysisId).catch((reason: unknown) => {
            setError(reason instanceof Error ? reason.message : 'Could not load the analysis result.')
          })
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

  const columns = result
    ? [
        ['Supporting', result.supporting],
        ['Contradicting', result.contradicting],
        ['Qualifying', result.qualifying],
      ] as const
    : []

  return (
    <main>
      <section className="panel form-panel">
        <p className="eyebrow">EvidenceSplit</p>
        <h1>Compare scientific evidence</h1>
        {demoClaims.length > 0 && (
          <p className="demo-notice">Demo mode is active. Choose a prepared claim for a deterministic presentation.</p>
        )}
        <form onSubmit={submit}>
          <label htmlFor="claim">Scientific claim</label>
          {demoClaims.length > 0 ? (
            <select id="claim" value={claim} onChange={(event) => setClaim(event.target.value)} required>
              {demoClaims.map((demoClaim) => <option key={demoClaim}>{demoClaim}</option>)}
            </select>
          ) : (
            <>
              <textarea id="claim" value={claim} onChange={(event) => setClaim(event.target.value)} required />
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
                    return combined.filter((file, index) => combined.findIndex(
                      (candidate) => candidate.name === file.name && candidate.size === file.size && candidate.lastModified === file.lastModified,
                    ) === index).slice(0, 5)
                  })
                  event.target.value = ''
                }}
              />
              {files.length > 0 && (
                <ul className="file-list">
                  {files.map((file) => (
                    <li key={`${file.name}-${file.size}-${file.lastModified}`}>
                      <span>{file.name}</span>
                      <button type="button" onClick={() => setFiles((current) => current.filter((item) => item !== file))}>Remove</button>
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
          <button disabled={submitting || !claim.trim()}>{submitting ? 'Analyzing…' : 'Analyze evidence'}</button>
        </form>
        {progress && (
          <section className="progress" aria-live="polite">
            <div><strong>{progress.message}</strong><span>{progress.progress}%</span></div>
            <progress value={progress.progress} max="100" />
            {progress.warning && <p className="warning">{progress.warning}</p>}
            {progress.error && <p className="error" role="alert">{progress.error}</p>}
          </section>
        )}
        {error && <p className="error" role="alert">{error}</p>}
      </section>

      {result?.status === 'FAILED' && (
        <section className="results">
          <p className="notice error" role="alert">
            {result.error_message ?? 'The analysis failed. Please try again.'}
          </p>
        </section>
      )}

      {result && result.status !== 'FAILED' && (
        <section className="results">
          <header className="result-header">
            <div>
              <p className="eyebrow">Exact submitted claim</p>
              <h2>{result.claim}</h2>
            </div>
            <span className="assessment-badge">{result.overall_assessment ?? 'Evidence grouped'}</span>
          </header>
          {result.warning_message && <p className="notice warning">{result.warning_message}</p>}
          {result.error_message && <p className="notice error">{result.error_message}</p>}
          <section className="summary-panel">
            <h2>Balanced comparison</h2>
            <p>{result.summary ?? 'The evidence was grouped, but a synthesized overview is unavailable.'}</p>
          </section>
          <section className="distribution">
            <div><strong>{result.retrieved_paper_count}</strong><span>Retrieved papers</span></div>
            <div><strong>{result.supporting.length}</strong><span>Supporting</span></div>
            <div><strong>{result.contradicting.length}</strong><span>Contradicting</span></div>
            <div><strong>{result.qualifying.length}</strong><span>Qualifying</span></div>
          </section>
          <h2>Retrieved evidence distribution</h2>
          <section className="evidence-grid">
            {columns.map(([label, cards]) => (
              <section className={`evidence-column ${label.toLowerCase()}`} key={label}>
                <h2>{label} <span>{cards.length}</span></h2>
                {cards.length
                  ? cards.map((card) => <EvidenceCardView card={card} key={card.document_id} />)
                  : <p className="empty">No retrieved papers in this group.</p>}
              </section>
            ))}
          </section>
          {result.limitations.length > 0 && (
            <section className="limitations">
              <h2>Limitations</h2>
              <ul>{result.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}</ul>
            </section>
          )}
        </section>
      )}
    </main>
  )
}

export default App
