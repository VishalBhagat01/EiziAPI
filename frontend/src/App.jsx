import { useState } from 'react'
import './App.css'

const API_URL = 'http://localhost:8000'

function App() {
  const [projectName, setProjectName] = useState('')
  const [description, setDescription] = useState('')
  const [authType, setAuthType] = useState('bearer_token')
  const [codeLanguage, setCodeLanguage] = useState('javascript')
  const [numEndpoints, setNumEndpoints] = useState(5)
  const [loading, setLoading] = useState(false)
  const [pdfLoading, setPdfLoading] = useState(false)
  const [status, setStatus] = useState(null) // { type: 'loading'|'success'|'error', msg: '' }
  const [result, setResult] = useState(null)
  const [expandedEndpoints, setExpandedEndpoints] = useState({})

  const buildPayload = () => ({
    project_name: projectName || 'My API',
    description,
    auth_type: authType,
    code_language: codeLanguage,
    num_endpoints: parseInt(numEndpoints) || 5,
  })

  const handleGenerate = async () => {
    if (!description.trim()) {
      setStatus({ type: 'error', msg: 'Please describe your API first.' })
      return
    }
    setLoading(true)
    setStatus({ type: 'loading', msg: 'Generating API specification... This may take 15-30 seconds.' })
    setResult(null)

    try {
      const res = await fetch(`${API_URL}/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(buildPayload()),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Server error')
      }
      const data = await res.json()
      setResult(data)
      setStatus({ type: 'success', msg: `Generated ${data.total_endpoints} endpoints successfully.` })
    } catch (err) {
      setStatus({ type: 'error', msg: err.message })
    } finally {
      setLoading(false)
    }
  }

  const handleDownloadPDF = async () => {
    if (!description.trim()) {
      setStatus({ type: 'error', msg: 'Please describe your API first.' })
      return
    }
    setPdfLoading(true)
    setStatus({ type: 'loading', msg: 'Generating PDF documentation...' })

    try {
      const res = await fetch(`${API_URL}/generate/pdf`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(buildPayload()),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'PDF generation failed')
      }
      const blob = await res.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `APIGenie_${(projectName || 'API').replace(/\s+/g, '_')}_Docs.pdf`
      document.body.appendChild(a)
      a.click()
      a.remove()
      window.URL.revokeObjectURL(url)
      setStatus({ type: 'success', msg: 'PDF downloaded successfully!' })
    } catch (err) {
      setStatus({ type: 'error', msg: err.message })
    } finally {
      setPdfLoading(false)
    }
  }

  const toggleEndpoint = (index) => {
    setExpandedEndpoints(prev => ({ ...prev, [index]: !prev[index] }))
  }

  const doc = result?.documentation

  return (
    <div className="app">
      {/* ── Header ── */}
      <header className="header">
        <div className="logo">
          <span className="logo-icon">⚡</span>
          <h1>API-Genie</h1>
        </div>
        <span className="header-tag">v1.0.0</span>
      </header>

      {/* ── Main ── */}
      <main className="main">
        {/* Hero */}
        <section className="hero">
          <h2>Describe it. <span className="gradient">Generate it.</span></h2>
          <p>Tell us what API you need — we'll generate the spec, mock data, docs, and tests instantly.</p>
        </section>

        {/* Form */}
        <div className="form-card">
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="project-name">Project Name</label>
              <input
                id="project-name"
                type="text"
                placeholder="e.g. FinTech Wallet API"
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
              />
            </div>
            <div className="form-group">
              <label htmlFor="auth-type">Authentication</label>
              <select id="auth-type" value={authType} onChange={(e) => setAuthType(e.target.value)}>
                <option value="bearer_token">Bearer Token</option>
                <option value="api_key">API Key</option>
                <option value="basic_auth">Basic Auth</option>
                <option value="none">No Auth</option>
              </select>
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="api-description">Describe Your API</label>
            <textarea
              id="api-description"
              placeholder="e.g. An e-commerce API for a clothing store with products, categories, shopping cart, orders, user profiles, and payment processing..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={4}
            />
            <p className="form-hint">Be specific — mention entities, actions, and business rules for better results.</p>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="num-endpoints">Number of Endpoints</label>
              <input
                id="num-endpoints"
                type="number"
                min={1}
                max={15}
                value={numEndpoints}
                onChange={(e) => setNumEndpoints(e.target.value)}
              />
            </div>
            <div className="form-group">
              <label htmlFor="code-language">Language</label>
              <select id="code-language" value={codeLanguage} onChange={(e) => setCodeLanguage(e.target.value)}>
                <option value="javascript">JavaScript</option>
                <option value="python">Python</option>
              </select>
            </div>
          </div>

          {/* Buttons */}
          <div className="btn-row">
            <button
              id="btn-generate"
              className="btn btn-primary"
              onClick={handleGenerate}
              disabled={loading || pdfLoading}
            >
              {loading ? <><span className="spinner" /> Generating...</> : <>⚡ Generate Spec</>}
            </button>
            <button
              id="btn-pdf"
              className="btn btn-secondary"
              onClick={handleDownloadPDF}
              disabled={loading || pdfLoading}
            >
              {pdfLoading ? <><span className="spinner" /> Creating PDF...</> : <>📄 Download PDF</>}
            </button>
          </div>

          {/* Status */}
          {status && (
            <div className={`status-bar ${status.type}`}>
              {status.type === 'loading' && <span className="spinner" />}
              {status.type === 'success' && '✓'}
              {status.type === 'error' && '✗'}
              {status.msg}
            </div>
          )}
        </div>

        {/* ── Results ── */}
        {doc && (
          <section className="results">
            <div className="results-header">
              <h3>📋 {doc.project_name}</h3>
              <div className="results-stats">
                <span className="stat"><span className="num">{doc.endpoints?.length || 0}</span> Endpoints</span>
                <span className="stat"><span className="num">{doc.test_cases?.length || 0}</span> Tests</span>
              </div>
            </div>

            {/* Overview */}
            {doc.overview && (
              <div className="code-block" style={{ marginBottom: 16 }}>
                <pre style={{ color: 'var(--text-secondary)' }}>{doc.overview}</pre>
              </div>
            )}

            {/* Endpoints */}
            {doc.endpoints?.map((ep, i) => (
              <div className="endpoint-card" key={i}>
                <div className="endpoint-head" onClick={() => toggleEndpoint(i)}>
                  <span className={`method-badge ${ep.method?.toLowerCase()}`}>
                    {ep.method}
                  </span>
                  <span className="endpoint-path">{ep.path}</span>
                  <span className="endpoint-summary">{ep.summary}</span>
                  <span className={`endpoint-toggle ${expandedEndpoints[i] ? 'open' : ''}`}>▼</span>
                </div>

                {expandedEndpoints[i] && (
                  <div className="endpoint-body">
                    {ep.description && <p className="endpoint-desc">{ep.description}</p>}

                    {/* Request Schema */}
                    {ep.request_schema && ep.request_schema.length > 0 && (
                      <>
                        <p className="schema-title">Request Body</p>
                        <table className="schema-table">
                          <thead>
                            <tr><th>Field</th><th>Type</th><th>Description</th></tr>
                          </thead>
                          <tbody>
                            {ep.request_schema.map((f, j) => (
                              <tr key={j}>
                                <td className="fname">{f.name}</td>
                                <td className="ftype">{f.type}</td>
                                <td className="fdesc">{f.description}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </>
                    )}

                    {/* Response Schema */}
                    {ep.response_schema && ep.response_schema.length > 0 && (
                      <>
                        <p className="schema-title">Response Schema</p>
                        <table className="schema-table">
                          <thead>
                            <tr><th>Field</th><th>Type</th><th>Description</th></tr>
                          </thead>
                          <tbody>
                            {ep.response_schema.map((f, j) => (
                              <tr key={j}>
                                <td className="fname">{f.name}</td>
                                <td className="ftype">{f.type}</td>
                                <td className="fdesc">{f.description}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </>
                    )}

                    {/* Sample Response */}
                    {ep.sample_response && (
                      <>
                        <p className="schema-title">Sample Response</p>
                        <div className="code-block">
                          <pre>{JSON.stringify(ep.sample_response, null, 2)}</pre>
                        </div>
                      </>
                    )}

                    {/* Code Example */}
                    {ep.code_example && (
                      <>
                        <p className="schema-title">Code Example</p>
                        <div className="code-block">
                          <pre>{ep.code_example}</pre>
                        </div>
                      </>
                    )}

                    {/* Status Codes */}
                    {ep.status_codes && (
                      <>
                        <p className="schema-title">Status Codes</p>
                        <table className="schema-table">
                          <thead>
                            <tr><th>Code</th><th>Description</th></tr>
                          </thead>
                          <tbody>
                            {Object.entries(ep.status_codes).map(([code, desc], j) => (
                              <tr key={j}>
                                <td className="fname">{code}</td>
                                <td className="fdesc">{desc}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </>
                    )}
                  </div>
                )}
              </div>
            ))}

            {/* Test Cases */}
            {doc.test_cases && doc.test_cases.length > 0 && (
              <div className="tests-section" style={{ marginTop: '40px' }}>
                <h3 style={{ marginBottom: '20px', borderBottom: '1px solid var(--border)', paddingBottom: '10px' }}>
                  🧪 Testing Requirements
                </h3>
                <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginBottom: '20px' }}>
                  These validation scenarios should be implemented in your CI/CD test suite ({codeLanguage === 'javascript' ? 'e.g., Jest, Supertest' : 'e.g., Pytest'}).
                </p>
                <div style={{ display: 'grid', gap: '16px' }}>
                  {doc.test_cases.map((tc, i) => (
                    <div className="test-card" key={i} style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '20px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <div style={{ fontSize: '16px', fontWeight: 'bold', color: 'var(--text-primary)' }}>
                          {tc.name.replace(/_/g, ' ').replace(/^test /i, '').replace(/\b\w/g, l => l.toUpperCase())}
                        </div>
                        <div className={`method-badge ${tc.method?.toLowerCase()}`}>
                          {tc.method}
                        </div>
                      </div>
                      
                      <p style={{ color: 'var(--text-secondary)', fontSize: '14px', margin: 0 }}>{tc.description}</p>
                      
                      <div style={{ display: 'flex', alignItems: 'center', gap: '16px', padding: '12px', background: 'var(--bg-input)', borderRadius: '6px', border: '1px solid var(--border)' }}>
                        <div style={{ flex: 1 }}>
                          <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)', letterSpacing: '0.5px' }}>Target Endpoint</span>
                          <div style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', color: 'var(--accent-cyan)', marginTop: '4px' }}>{tc.endpoint}</div>
                        </div>
                        <div style={{ paddingLeft: '16px', borderLeft: '1px solid var(--border)' }}>
                          <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)', letterSpacing: '0.5px' }}>Expected Status</span>
                          <div style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', color: 'var(--text-primary)', marginTop: '4px' }}>{tc.expected_status}</div>
                        </div>
                      </div>

                      {tc.assertions && tc.assertions.length > 0 && (
                        <div>
                          <span style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Validation Criteria:</span>
                          <ul style={{ margin: '8px 0 0 20px', padding: 0, color: 'var(--text-light)', fontSize: '14px' }}>
                            {tc.assertions.map((a, j) => (
                              <li key={j} style={{ paddingBottom: '6px' }}>{a}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </section>
        )}
      </main>

      {/* ── Footer ── */}
      <footer className="footer">
        API-Genie — Built with FastAPI, LangChain, and Groq
      </footer>
    </div>
  )
}

export default App
