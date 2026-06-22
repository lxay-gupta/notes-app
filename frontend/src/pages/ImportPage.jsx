import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { importsApi } from '../api/imports'
import { AppShell } from '../components/layout/AppShell'
import { Spinner } from '../components/ui/Spinner'
import { extractError, fmtDateTime } from '../utils/helpers'
import toast from 'react-hot-toast'

const ACCEPTED = ['.txt', '.md', '.csv', '.json']
const FORMAT_INFO = [
  { ext: '.txt', label: 'Plain text', desc: 'First line becomes the title' },
  { ext: '.md',  label: 'Markdown',   desc: '# Heading stripped to title' },
  { ext: '.csv', label: 'CSV',        desc: 'Formatted table with row summary' },
  { ext: '.json',label: 'JSON',       desc: 'Pretty-printed with key-based title' },
]

export function ImportPage() {
  const [uploading, setUploading] = useState(false)
  const [result,    setResult]    = useState(null)
  const [history,   setHistory]   = useState([])
  const [histLoading, setHistLoading] = useState(true)
  const [dragging,  setDragging]  = useState(false)
  const inputRef = useRef(null)

  const fetchHistory = useCallback(async () => {
    try {
      const { data } = await importsApi.history({ limit: 20 })
      setHistory(data)
    } catch { /* silent */ }
    finally { setHistLoading(false) }
  }, [])

  useEffect(() => { fetchHistory() }, [fetchHistory])

  const doUpload = async (file) => {
    if (!file) return
    const ext = '.' + file.name.split('.').pop().toLowerCase()
    if (!ACCEPTED.includes(ext)) {
      toast.error(`Unsupported format. Use: ${ACCEPTED.join(', ')}`)
      return
    }
    if (file.size > 5 * 1024 * 1024) {
      toast.error('File too large. Maximum 5 MB.')
      return
    }

    setUploading(true)
    setResult(null)
    try {
      const { data } = await importsApi.upload(file)
      setResult(data)
      if (data.status === 'success') {
        toast.success(`Imported as "${data.import_record?.note_id ? 'new note' : 'note'}"`)
      } else {
        toast.error(`Import failed: ${data.message}`)
      }
      fetchHistory()
    } catch (err) {
      toast.error(extractError(err))
    } finally {
      setUploading(false)
    }
  }

  const handleFile = (e) => doUpload(e.target.files?.[0])

  const handleDrop = (e) => {
    e.preventDefault()
    setDragging(false)
    doUpload(e.dataTransfer.files?.[0])
  }

  const statusBadge = (status) => {
    const cls = {
      success: 'bg-green-50 text-green-700 border border-green-200',
      failed:  'bg-red-50 text-red-700 border border-red-200',
      pending: 'bg-amber-50 text-amber-700 border border-amber-200',
    }[status] ?? 'bg-surface-muted text-ink-muted'
    return (
      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${cls}`}>
        {status}
      </span>
    )
  }

  return (
    <AppShell>
      <div className="max-w-2xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-lg font-semibold text-ink">Import a file</h1>
          <p className="text-sm text-ink-muted mt-0.5">
            Upload a file and it becomes a note instantly.
          </p>
        </div>

        {/* Drop zone */}
        <div
          onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
          onClick={() => !uploading && inputRef.current?.click()}
          className={`relative flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed
                      cursor-pointer transition-colors duration-150 py-12 px-6 mb-6 text-center
                      ${dragging ? 'border-accent bg-accent-subtle' : 'border-ink-faint hover:border-accent hover:bg-surface-muted'}`}
        >
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPTED.join(',')}
            onChange={handleFile}
            className="sr-only"
            aria-label="File input"
          />

          {uploading ? (
            <>
              <Spinner size="lg" className="text-accent" />
              <p className="text-sm text-ink-muted">Importing…</p>
            </>
          ) : (
            <>
              <div className="w-10 h-10 rounded-full bg-surface-muted flex items-center justify-center text-ink-muted">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                    d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                </svg>
              </div>
              <div>
                <p className="text-sm font-medium text-ink">
                  Drop a file here, or <span className="text-accent">browse</span>
                </p>
                <p className="text-xs text-ink-muted mt-0.5">
                  {ACCEPTED.join(', ')} · max 5 MB
                </p>
              </div>
            </>
          )}
        </div>

        {/* Result banner */}
        {result && !uploading && (
          <div className={`mb-6 rounded-lg p-4 border animate-slide-in ${
            result.status === 'success'
              ? 'bg-green-50 border-green-200'
              : 'bg-red-50 border-red-200'
          }`}>
            <div className="flex items-start gap-3">
              {result.status === 'success' ? (
                <svg className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
              ) : (
                <svg className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              )}
              <div className="flex-1">
                <p className={`text-sm font-medium ${result.status === 'success' ? 'text-green-800' : 'text-red-800'}`}>
                  {result.message}
                </p>
                {result.status === 'success' && result.note_id && (
                  <Link
                    to={`/notes/${result.note_id}`}
                    className="mt-1 inline-block text-xs text-green-700 underline hover:no-underline"
                  >
                    Open note →
                  </Link>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Format guide */}
        <div className="mb-8">
          <h2 className="text-xs font-medium text-ink-muted uppercase tracking-wide mb-3">
            Supported formats
          </h2>
          <div className="grid grid-cols-2 gap-2">
            {FORMAT_INFO.map(f => (
              <div key={f.ext} className="flex items-start gap-2.5 p-3 bg-white border border-ink-faint rounded-lg">
                <span className="font-mono text-xs text-accent font-medium flex-shrink-0">{f.ext}</span>
                <div>
                  <p className="text-xs font-medium text-ink">{f.label}</p>
                  <p className="text-xs text-ink-muted mt-0.5">{f.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Import history */}
        <div>
          <h2 className="text-xs font-medium text-ink-muted uppercase tracking-wide mb-3">
            Recent imports
          </h2>
          {histLoading ? (
            <div className="flex justify-center py-6">
              <Spinner className="text-ink-faint" />
            </div>
          ) : history.length === 0 ? (
            <p className="text-sm text-ink-muted text-center py-6">No imports yet.</p>
          ) : (
            <div className="bg-white border border-ink-faint rounded-lg overflow-hidden">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-ink-faint">
                    <th className="text-left px-4 py-2.5 text-ink-muted font-medium">File</th>
                    <th className="text-left px-4 py-2.5 text-ink-muted font-medium">Status</th>
                    <th className="text-left px-4 py-2.5 text-ink-muted font-medium">Date</th>
                    <th className="text-left px-4 py-2.5 text-ink-muted font-medium">Note</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((h, i) => (
                    <tr key={h.id} className={`${i !== history.length - 1 ? 'border-b border-ink-faint' : ''}`}>
                      <td className="px-4 py-2.5 text-ink font-mono truncate max-w-[160px]">
                        {/* uploaded_file not nested in history, show id truncated */}
                        {h.uploaded_file_id?.slice(0, 8)}…
                      </td>
                      <td className="px-4 py-2.5">{statusBadge(h.status)}</td>
                      <td className="px-4 py-2.5 text-ink-muted whitespace-nowrap">
                        {fmtDateTime(h.created_at)}
                      </td>
                      <td className="px-4 py-2.5">
                        {h.note_id ? (
                          <Link
                            to={`/notes/${h.note_id}`}
                            className="text-accent hover:underline font-mono"
                          >
                            {h.note_id.slice(0, 8)}…
                          </Link>
                        ) : (
                          <span className="text-ink-faint">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </AppShell>
  )
}
