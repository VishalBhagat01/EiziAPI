import { useEffect, useRef } from 'react'
import Prism from 'prismjs'
import 'prismjs/components/prism-python'
import 'prismjs/components/prism-javascript'
import 'prismjs/components/prism-json'
import 'prismjs/components/prism-sql'
import 'prismjs/components/prism-bash'
import 'prismjs/components/prism-markdown'


// ─────────────────────────────────────────────
// Step 1: Unescape — Fix LLM escape sequences
// ─────────────────────────────────────────────

function unescapeLLM(raw) {
  if (!raw || typeof raw !== 'string') return ''

  let code = raw.trim()

  // Strip wrapping quotes
  if (
    (code.startsWith('"') && code.endsWith('"')) ||
    (code.startsWith("'") && code.endsWith("'"))
  ) {
    code = code.slice(1, -1)
  }

  // Replace literal escape sequences with real characters
  code = code
    .replace(/\\n/g, '\n')
    .replace(/\\t/g, '  ')
    .replace(/\\"/g, '"')
    .replace(/\\'/g, "'")
    .replace(/\\\\/g, '\\')

  // Collapse 3+ blank lines into 2
  code = code.replace(/\n{3,}/g, '\n\n')

  return code.trim()
}


// ─────────────────────────────────────────────
// Step 2: Prettify — Add line breaks + indentation
// ─────────────────────────────────────────────

/**
 * Checks whether the code looks like it's been squished onto too few lines.
 * If lines average over 120 chars, it probably needs formatting.
 */
function needsPrettifying(code) {
  const lines = code.split('\n')
  if (lines.length <= 2 && code.length > 100) return true

  const avgLen = code.length / Math.max(lines.length, 1)
  return avgLen > 120
}

/**
 * Lightweight JavaScript / generic code prettifier.
 *
 * Rules:
 *   - After `{`  → newline, increase indent
 *   - After `}`  → decrease indent, newline
 *   - After `;`  → newline (same indent)
 *   - After `,`  → newline when inside object/array (depth > 0)
 *   - Skips formatting inside string literals
 *   - Adds proper 2-space indentation
 */
function prettifyJS(code) {
  let result = ''
  let indent = 0
  let inString = false   // currently inside a string?
  let stringChar = ''     // which quote character opened it (' or ")
  let i = 0

  const INDENT = '  '

  function addNewline() {
    result += '\n' + INDENT.repeat(indent)
  }

  while (i < code.length) {
    const ch = code[i]
    const prev = i > 0 ? code[i - 1] : ''

    // ── Handle string literals (don't format inside them) ──
    if (inString) {
      result += ch
      // End of string? (ignore escaped quotes)
      if (ch === stringChar && prev !== '\\') {
        inString = false
      }
      i++
      continue
    }

    // Start of string?
    if (ch === '"' || ch === "'" || ch === '`') {
      inString = true
      stringChar = ch
      result += ch
      i++
      continue
    }

    // ── Handle single-line comments ──
    if (ch === '/' && i + 1 < code.length && code[i + 1] === '/') {
      // Consume until end of line
      let comment = ''
      while (i < code.length && code[i] !== '\n') {
        comment += code[i]
        i++
      }
      result += comment
      continue
    }

    // ── Structural characters ──

    if (ch === '{') {
      // Trim trailing whitespace before the brace
      result = result.replace(/\s+$/, ' ')
      result += ' {'
      indent++
      addNewline()
      i++
      // Skip whitespace after brace
      while (i < code.length && (code[i] === ' ' || code[i] === '\t')) i++
      continue
    }

    if (ch === '}') {
      indent = Math.max(0, indent - 1)
      // Trim trailing whitespace
      result = result.replace(/\s+$/, '')
      addNewline()
      result += '}'
      i++
      // If next non-space char is NOT `)`, `,`, `;`, `.`, `else`, add newline
      let peek = i
      while (peek < code.length && (code[peek] === ' ' || code[peek] === '\t')) peek++
      const nextCh = code[peek] || ''
      if (nextCh && nextCh !== ')' && nextCh !== ',' && nextCh !== ';' && nextCh !== '.' && nextCh !== '\n') {
        addNewline()
      }
      continue
    }

    if (ch === ';') {
      result += ';'
      i++
      // Skip whitespace after semicolon
      while (i < code.length && (code[i] === ' ' || code[i] === '\t')) i++
      // Only add newline if next char is NOT a newline already and NOT end of string
      if (i < code.length && code[i] !== '\n' && code[i] !== '}') {
        addNewline()
      }
      continue
    }

    if (ch === ',' && indent > 0) {
      result += ','
      i++
      // Skip whitespace after comma
      while (i < code.length && (code[i] === ' ' || code[i] === '\t')) i++
      if (i < code.length && code[i] !== '\n') {
        addNewline()
      }
      continue
    }

    // ── Arrow functions: => { should stay on same line ──
    // (handled naturally by the `{` rule above)

    // ── Existing newline — re-indent it properly ──
    if (ch === '\n') {
      result += '\n'
      i++
      // Skip existing whitespace after newline
      while (i < code.length && (code[i] === ' ' || code[i] === '\t')) i++
      // Add proper indentation
      result += INDENT.repeat(indent)
      continue
    }

    // ── Normal character ──
    result += ch
    i++
  }

  // Clean up: remove lines that are only whitespace, collapse multiple blank lines
  return result
    .split('\n')
    .map(line => line.trimEnd())
    .join('\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

/**
 * SQL prettifier — breaks at semicolons and major keywords.
 */
function prettifySQL(code) {
  // Split statements on semicolons
  let formatted = code.replace(/;\s*/g, ';\n\n')

  // Add newlines before major SQL keywords
  const keywords = ['SELECT', 'FROM', 'WHERE', 'JOIN', 'LEFT JOIN', 'RIGHT JOIN',
    'INNER JOIN', 'ORDER BY', 'GROUP BY', 'HAVING', 'INSERT INTO', 'VALUES',
    'UPDATE', 'SET', 'DELETE FROM', 'CREATE TABLE', 'ALTER TABLE', 'DROP TABLE',
    'AND', 'OR', 'ON', 'LIMIT', 'OFFSET']

  keywords.forEach(kw => {
    // Add newline before keyword (case insensitive), but not at start of string
    const regex = new RegExp(`(?<!^)\\b(${kw})\\b`, 'gi')
    formatted = formatted.replace(regex, '\n  $1')
  })

  return formatted
    .split('\n')
    .map(line => line.trimEnd())
    .join('\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

/**
 * Python prettifier — breaks long chained method calls.
 */
function prettifyPython(code) {
  const lines = code.split('\n')
  const result = []

  for (const line of lines) {
    // If line is very long (>120 chars), try breaking at top-level commas
    if (line.length > 120) {
      // Simple: break at commas that are NOT inside parentheses beyond depth 1
      let depth = 0
      let current = ''
      let indent = line.match(/^(\s*)/)[1]
      let firstPart = true

      for (let i = 0; i < line.length; i++) {
        const ch = line[i]
        if (ch === '(' || ch === '[' || ch === '{') depth++
        if (ch === ')' || ch === ']' || ch === '}') depth--
        current += ch

        if (ch === ',' && depth <= 1 && current.length > 60) {
          result.push(current)
          current = indent + '    '
          firstPart = false
        }
      }
      if (current.trim()) result.push(current)
    } else {
      result.push(line)
    }
  }

  return result.join('\n').trim()
}


// ─────────────────────────────────────────────
// Step 3: Full pipeline — unescape → prettify
// ─────────────────────────────────────────────

export function formatCode(raw, language) {
  let code = unescapeLLM(raw)
  if (!code) return ''

  // Only prettify if the code looks squished
  if (needsPrettifying(code)) {
    const lang = (language || '').toLowerCase()

    if (['javascript', 'js', 'json'].includes(lang)) {
      code = prettifyJS(code)
    } else if (lang === 'sql') {
      code = prettifySQL(code)
    } else if (['python', 'py'].includes(lang)) {
      code = prettifyPython(code)
    } else {
      // Generic: at least break on semicolons and braces
      code = prettifyJS(code)
    }
  }

  return code
}


// ─────────────────────────────────────────────
// Language mapping for Prism.js
// ─────────────────────────────────────────────

function getPrismLanguage(lang) {
  const map = {
    javascript: 'javascript',
    js: 'javascript',
    python: 'python',
    py: 'python',
    json: 'json',
    sql: 'sql',
    bash: 'bash',
    shell: 'bash',
    markdown: 'markdown',
    md: 'markdown',
  }
  return map[lang?.toLowerCase()] || 'javascript'
}


// ─────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────

export default function CodeViewer({ code, language = 'javascript', showLineNumbers = true }) {
  const codeRef = useRef(null)
  const prismLang = getPrismLanguage(language)
  const formatted = formatCode(code, prismLang)
  const lines = formatted.split('\n')

  useEffect(() => {
    if (codeRef.current) {
      Prism.highlightElement(codeRef.current)
    }
  }, [formatted, prismLang])

  if (!formatted) {
    return (
      <div className="cv-empty">
        <span>No code to display</span>
      </div>
    )
  }

  return (
    <div className="cv-container">
      {/* Toolbar */}
      <div className="cv-toolbar">
        <span className="cv-lang-badge">{prismLang}</span>
        <span className="cv-line-count">{lines.length} lines</span>
      </div>

      {/* Code area */}
      <div className="cv-scroll">
        {showLineNumbers && (
          <div className="cv-line-numbers" aria-hidden="true">
            {lines.map((_, i) => (
              <span key={i}>{i + 1}</span>
            ))}
          </div>
        )}
        <pre className="cv-pre">
          <code ref={codeRef} className={`language-${prismLang}`}>
            {formatted}
          </code>
        </pre>
      </div>
    </div>
  )
}
