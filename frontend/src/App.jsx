import { useState, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import './App.css'

const API_URL = 'http://localhost:8000'

function App() {
  const location = useLocation()
  const [projectName, setProjectName] = useState(location.state?.projectName || '')
  const [description, setDescription] = useState('')
  const [authType, setAuthType] = useState('bearer_token')
  const [codeLanguage, setCodeLanguage] = useState('javascript')
  const [numEndpoints, setNumEndpoints] = useState(5)
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState(null) // { type: 'loading'|'success'|'error', msg: '' }
  const [result, setResult] = useState(null)
  const [expandedEndpoints, setExpandedEndpoints] = useState({})

  // Update project name if location state changes
  useEffect(() => {
    if (location.state?.projectName) {
      setProjectName(location.state.projectName)
    }
  }, [location.state])

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

  const getAllCodeSnippets = () => {
    if (!result || !result.documentation || !result.documentation.endpoints) {
      return ''
    }
    
    let code = ''
    
    // Add database setup if available
    if (result.documentation.database_setup) {
      code += `// ═══ DATABASE SETUP ═══\n`
      code += `// ${result.documentation.database_setup}\n\n`
    }
    
    // Add database models if available
    if (result.documentation.database_models) {
      code += `// ═══ DATABASE MODELS ═══\n`
      code += result.documentation.database_models + '\n\n'
    }
    
    // Add endpoints with both client and database code
    result.documentation.endpoints.forEach(endpoint => {
      code += `// ═══ ${endpoint.method} ${endpoint.path} ═══\n`
      code += `// ${endpoint.summary}\n\n`
      
      if (endpoint.code_example) {
        code += `// CLIENT CODE:\n`
        code += endpoint.code_example + '\n\n'
      }
      
      if (endpoint.database_code) {
        code += `// DATABASE CODE:\n`
        code += endpoint.database_code + '\n\n'
      }
      
      code += '\n'
    })
    
    return code
  }

  const handleDownloadCode = () => {
    const allCode = getAllCodeSnippets()
    if (!allCode) {
      setStatus({ type: 'error', msg: 'No code to download. Please generate the spec first.' })
      return
    }
    const blob = new Blob([allCode], { type: 'text/plain;charset=utf-8' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${(projectName || 'API').replace(/\s+/g, '_')}_endpoints.${codeLanguage === 'python' ? 'py' : 'js'}`
    document.body.appendChild(a)
    a.click()
    a.remove()
    window.URL.revokeObjectURL(url)
    setStatus({ type: 'success', msg: 'Code downloaded successfully!' })
  }

  const handleCopyCode = () => {
    const allCode = getAllCodeSnippets()
    if (!allCode) {
      setStatus({ type: 'error', msg: 'No code to copy. Please generate the spec first.' })
      return
    }
    navigator.clipboard.writeText(allCode).then(() => {
      setStatus({ type: 'success', msg: 'Code copied to clipboard!' })
    }, () => {
      setStatus({ type: 'error', msg: 'Failed to copy code.' })
    })
  }

  const [selectedCode, setSelectedCode] = useState(null) // { title: '', code: '', lang: '' }

  const toggleEndpoint = (index) => {
    setExpandedEndpoints(prev => ({ ...prev, [index]: !prev[index] }))
  }

  const openEditor = (title, code, lang) => {
    const formattedCode = typeof code === 'string' ? code : JSON.stringify(code, null, 2)
    setSelectedCode({ title, code: formattedCode, lang })
    document.body.style.overflow = 'hidden'
  }

  const closeEditor = () => {
    setSelectedCode(null)
    document.body.style.overflow = 'auto'
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
        <div className="header-nav">
          <Link to="/" className="header-link">Dashboard</Link>
          <span className="header-tag">v2.0.0</span>
        </div>
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

          <div className="btn-row">
            <button
              id="btn-generate"
              className="btn btn-primary"
              onClick={handleGenerate}
              disabled={loading}
            >
              {loading ? <><span className="spinner" /> Generating...</> : <>⚡ Generate Spec</>}
            </button>
            <div className="code-actions">
              <button
                className="btn btn-secondary"
                onClick={handleDownloadCode}
                disabled={!result || loading}
                title={!result ? "Generate a spec to download the code" : "Download all endpoint code"}
              >
                <>📦 Download Code</>
              </button>
              <button
                className="btn btn-secondary"
                onClick={handleCopyCode}
                disabled={!result || loading}
                title={!result ? "Generate a spec to copy the code" : "Copy all endpoint code"}
              >
                <>📋 Copy Code</>
              </button>
            </div>
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
                {result?.latency_ms !== undefined && (
                  <span className="stat"><span className="num">{result.cached ? '<1' : Math.round(result.latency_ms)}</span> ms</span>
                )}
                {result?.llm_provider && (
                  <span className="stat">{result.llm_provider}</span>
                )}
                {result?.cached && (
                  <span className="stat cached">⚡ Cached</span>
                )}
              </div>
            </div>

            {/* Overview & Global Actions */}
            <div className="results-actions" style={{ marginBottom: '24px', display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
              {doc.database_models && (
                <button className="btn btn-secondary" onClick={() => openEditor('Database Models', doc.database_models, codeLanguage)}>
                  🗄️ View Models
                </button>
              )}
              {doc.setup_instructions && (
                <button className="btn btn-secondary" onClick={() => openEditor('Setup Instructions', doc.setup_instructions, 'markdown')}>
                  📜 Setup Guide
                </button>
              )}
              {result && (
                <button className="btn btn-primary" onClick={() => openEditor('Full Project Implementation', getAllCodeSnippets(), codeLanguage)}>
                  🚀 Full Project Code
                </button>
              )}
            </div>

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

                    <div className="endpoint-actions">
                       {ep.code_example && (
                         <button className="btn-view-code" onClick={() => openEditor(`${ep.method} ${ep.path} - Client Code`, ep.code_example, codeLanguage)}>
                           Client Code
                         </button>
                       )}
                       {ep.database_code && (
                         <button className="btn-view-code" onClick={() => openEditor(`${ep.method} ${ep.path} - Database Handler`, ep.database_code, codeLanguage)}>
                           Database Code
                         </button>
                       )}
                    </div>

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
                        <div className="code-block small">
                          <pre>{JSON.stringify(ep.sample_response, null, 2)}</pre>
                        </div>
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
                <div style={{ display: 'grid', gap: '16px' }}>
                  {doc.test_cases.map((tc, i) => (
                    <div className="test-card" key={i} style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '20px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <div style={{ fontSize: '16px', fontWeight: 'bold', color: 'var(--text-primary)' }}>
                          {tc.name.replace(/_/g, ' ').replace(/^test /i, '').replace(/\b\w/g, l => l.toUpperCase())}
                        </div>
                        <button className="btn-view-code" onClick={() => openEditor(`Test: ${tc.name}`, tc.code, codeLanguage)}>
                          View Test Code
                        </button>
                      </div>
                      <p style={{ color: 'var(--text-secondary)', fontSize: '14px', margin: 0 }}>{tc.description}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </section>
        )}
      </main>

      {/* ── Editor Modal ── */}
      {selectedCode && (
        <div className="editor-overlay" onClick={closeEditor}>
          <div className="editor-modal" onClick={e => e.stopPropagation()}>
            <div className="editor-header">
              <h3>{selectedCode.title}</h3>
              <button className="close-btn" onClick={closeEditor}>&times;</button>
            </div>
            <div className="editor-body">
              <pre><code>{selectedCode.code}</code></pre>
            </div>
            <div className="editor-footer">
              <button className="btn btn-secondary" onClick={() => {
                navigator.clipboard.writeText(selectedCode.code)
                alert('Copied to clipboard!')
              }}>Copy Code</button>
            </div>
          </div>
        </div>
      )}

      {/* ── Footer ── */}
      <footer className="footer">
        API-Genie v2.0 — FastAPI + LangChain + Groq/Gemini | Cached LLM with Provider Fallback
      </footer>
    </div>
  )
}

export default App
