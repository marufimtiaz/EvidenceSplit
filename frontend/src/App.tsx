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
  default_enabled: boolean
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
    <article className="evidence-card">
      <div className="card-badges">
        <span className={`source-badge ${card.source_type.toLowerCase()}`}>{sourceLabels[card.source_type]}</span>
        <span className={`stance-badge ${card.paper_stance.toLowerCase()}`}>{card.paper_stance.toLowerCase()}</span>
      </div>
      <h3>{card.title}</h3>
      <p className="metadata">
        {card.authors.length ? card.authors.join(', ') : 'Authors unavailable'}
        {card.year ? ` · ${card.year}` : ''}
      </p>
      <p className="paper-summary">{card.paper_summary}</p>
      <div className="findings-list">
        {card.findings.map((finding) => (
          <details key={finding.id}>
            <summary>
              <span>Evidence excerpt</span>
              <span className="confidence">{Math.round(finding.confidence * 100)}% confidence</span>
            </summary>
            <blockquote>“{finding.evidence_quote}”</blockquote>
            <p>{finding.explanation}</p>
            {finding.conditions && <p className="conditions"><strong>Conditions</strong>{finding.conditions}</p>}
            <div className="finding-footer">
              {finding.page_start && (
                <span>Page {finding.page_start}{finding.page_end !== finding.page_start ? `–${finding.page_end}` : ''}</span>
              )}
              <code title={finding.id}>{finding.id.slice(0, 8)}…</code>
            </div>
          </details>
        ))}
      </div>
      {sourceHref && (
        <a className="source-link" href={sourceHref} target="_blank" rel="noreferrer">
          Open source <span aria-hidden="true">↗</span>
        </a>
      )}
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
  const [demoClaim, setDemoClaim] = useState('')
  const [demoMode, setDemoMode] = useState(false)
  const sourceRef = useRef<EventSource | null>(null)

  useEffect(() => {
    void fetch(`${API_BASE}/api/analyses/demo-claims`)
      .then((response) => response.ok ? response.json() as Promise<DemoConfig> : null)
      .then((config) => {
        if (config?.claims.length) {
          setDemoClaims(config.claims)
          setDemoClaim(config.claims[0])
          setDemoMode(config.default_enabled)
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

    const selectedClaim = demoMode ? demoClaim : claim
    const body = new FormData()
    body.append('claim', selectedClaim)
    body.append('demo_mode', String(demoMode))
    if (!demoMode) files.forEach((file) => body.append('files', file))

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
  const selectedClaim = demoMode ? demoClaim : claim

  return (
    <div className="app-shell">
      <nav className="topbar">
        <a className="brand" href="#top" aria-label="EvidenceSplit home">
          <span className="brand-mark" aria-hidden="true"><i /><i /></span>
          <span>Evidence<span>Split</span></span>
        </a>
        <div className="topbar-meta">
          <span className="system-dot" /> Scientific evidence workspace
        </div>
      </nav>

      <main id="top">
        <section className="hero">
          <div className="hero-copy">
            <p className="eyebrow"><span /> Evidence intelligence</p>
            <h1>Every paper has a position. <em>See the split.</em></h1>
            <p className="hero-lede">
              Turn research papers into a balanced, traceable view of what supports, contradicts, or qualifies a scientific claim.
            </p>
            <div className="trust-row">
              <div><strong>01</strong><span>Upload research</span></div>
              <div><strong>02</strong><span>Extract evidence</span></div>
              <div><strong>03</strong><span>Compare positions</span></div>
            </div>
          </div>

          <section className="analysis-card">
            <div className="card-heading">
              <div>
                <p className="section-kicker">New analysis</p>
                <h2>Test a scientific claim</h2>
              </div>
              <span className={`mode-status ${demoMode ? 'is-demo' : ''}`}>{demoMode ? 'Demo' : 'Live'}</span>
            </div>

            {demoClaims.length > 0 && (
              <div className="mode-tabs" aria-label="Analysis mode">
                <button type="button" className={!demoMode ? 'active' : ''} onClick={() => setDemoMode(false)}>
                  Live analysis
                </button>
                <button type="button" className={demoMode ? 'active' : ''} onClick={() => setDemoMode(true)}>
                  Demo mode
                </button>
              </div>
            )}

            <form onSubmit={submit}>
              <label className="field-label" htmlFor="claim">
                Scientific claim <span>{demoMode ? 'Prepared scenario' : 'Be specific and testable'}</span>
              </label>
              {demoMode ? (
                <select id="claim" value={demoClaim} onChange={(event) => setDemoClaim(event.target.value)} required>
                  {demoClaims.map((preparedClaim) => <option key={preparedClaim}>{preparedClaim}</option>)}
                </select>
              ) : (
                <>
                  <textarea
                    id="claim"
                    value={claim}
                    onChange={(event) => setClaim(event.target.value)}
                    placeholder="e.g. Regular aerobic exercise reduces resting blood pressure in adults with hypertension."
                    required
                  />
                  <div className="upload-heading">
                    <label className="field-label" htmlFor="files">Research papers</label>
                    <span>{files.length}/5 PDFs</span>
                  </div>
                  <label className="upload-zone" htmlFor="files">
                    <span className="upload-icon" aria-hidden="true">↑</span>
                    <span><strong>Choose PDF files</strong><small>or add another batch · 20 MB each</small></span>
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
                  </label>
                  {files.length > 0 && (
                    <ul className="file-list">
                      {files.map((file) => (
                        <li key={`${file.name}-${file.size}-${file.lastModified}`}>
                          <span className="file-type">PDF</span>
                          <span className="file-name"><strong>{file.name}</strong><small>{(file.size / 1024 / 1024).toFixed(1)} MB</small></span>
                          <button type="button" aria-label={`Remove ${file.name}`} onClick={() => setFiles((current) => current.filter((item) => item !== file))}>×</button>
                        </li>
                      ))}
                    </ul>
                  )}
                </>
              )}
              {demoMode && <p className="demo-note"><span>◆</span> Prepared evidence runs without Gemini or uploaded files.</p>}
              <button className="analyze-button" disabled={submitting || !selectedClaim.trim()}>
                <span>{submitting ? 'Analyzing evidence' : 'Analyze evidence'}</span>
                <span aria-hidden="true">{submitting ? '···' : '→'}</span>
              </button>
            </form>

            {progress && (
              <section className="progress-panel" aria-live="polite">
                <div className="progress-heading">
                  <span className={submitting ? 'pulse-dot' : 'complete-dot'} />
                  <div><strong>{progress.message}</strong><small>{progress.stage.replaceAll('_', ' ').toLowerCase()}</small></div>
                  <b>{progress.progress}%</b>
                </div>
                <div className="progress-track"><span style={{ width: `${progress.progress}%` }} /></div>
                {progress.warning && <p className="inline-message warning">{progress.warning}</p>}
                {progress.error && <p className="inline-message error" role="alert">{progress.error}</p>}
              </section>
            )}
            {error && <p className="inline-message error" role="alert">{error}</p>}
          </section>
        </section>

        {result?.status === 'FAILED' && (
          <section className="failure-card">
            <span aria-hidden="true">!</span>
            <div><strong>Analysis could not be completed</strong><p>{result.error_message ?? 'Please try again.'}</p></div>
          </section>
        )}

        {result && result.status !== 'FAILED' && (
          <section className="results">
            <header className="result-header">
              <div>
                <p className="section-kicker">Evidence assessment</p>
                <h2>{result.claim}</h2>
              </div>
              <span className={`assessment-badge ${result.overall_assessment?.toLowerCase() ?? ''}`}>
                <i /> {result.overall_assessment?.replaceAll('_', ' ') ?? 'Evidence grouped'}
              </span>
            </header>

            {result.warning_message && <p className="notice warning">{result.warning_message}</p>}
            {result.error_message && <p className="notice error">{result.error_message}</p>}

            <div className="overview-grid">
              <section className="summary-panel">
                <p className="section-kicker">Balanced comparison</p>
                <h3>What the evidence says</h3>
                <p>{result.summary ?? 'The evidence was grouped, but a synthesized overview is unavailable.'}</p>
              </section>
              <section className="distribution" aria-label="Evidence distribution">
                <div className="total"><strong>{result.retrieved_paper_count}</strong><span>Papers reviewed</span></div>
                <div className="supporting"><strong>{result.supporting.length}</strong><span>Supporting</span></div>
                <div className="contradicting"><strong>{result.contradicting.length}</strong><span>Contradicting</span></div>
                <div className="qualifying"><strong>{result.qualifying.length}</strong><span>Qualifying</span></div>
              </section>
            </div>

            <div className="evidence-heading">
              <div><p className="section-kicker">Source-level findings</p><h2>Evidence distribution</h2></div>
              <p>Open each excerpt to inspect the exact language behind the classification.</p>
            </div>
            <section className="evidence-grid">
              {columns.map(([label, cards]) => (
                <section className={`evidence-column evidence-${label.toLowerCase()}`} key={label}>
                  <header><span className="column-dot" /><h2>{label}</h2><b>{cards.length}</b></header>
                  {cards.length
                    ? cards.map((card) => <EvidenceCardView card={card} key={card.document_id} />)
                    : <p className="empty">No papers were placed in this group.</p>}
                </section>
              ))}
            </section>

            {result.limitations.length > 0 && (
              <section className="limitations">
                <div className="limitations-icon" aria-hidden="true">i</div>
                <div><p className="section-kicker">Read with context</p><h2>Limitations</h2>
                  <ul>{result.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}</ul>
                </div>
              </section>
            )}
          </section>
        )}
      </main>

      <footer><span>EvidenceSplit</span><p>Evidence organized. Uncertainty preserved.</p></footer>
    </div>
  )
}

export default App
