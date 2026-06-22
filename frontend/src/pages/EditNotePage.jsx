import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { notesApi } from '../api/notes'
import { AppShell } from '../components/layout/AppShell'
import { TagManager } from '../components/tags/TagManager'
import { Spinner } from '../components/ui/Spinner'
import { extractError, fmtDateTime } from '../utils/helpers'
import toast from 'react-hot-toast'

export function EditNotePage() {
  const { id }   = useParams()
  const navigate = useNavigate()

  const [note,    setNote]    = useState(null)
  const [title,   setTitle]   = useState('')
  const [content, setContent] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving,  setSaving]  = useState(false)
  const [dirty,   setDirty]   = useState(false)

  useEffect(() => {
    const fetch = async () => {
      try {
        const { data } = await notesApi.get(id)
        setNote(data)
        setTitle(data.title)
        setContent(data.content)
      } catch (err) {
        toast.error(extractError(err))
        navigate('/dashboard')
      } finally {
        setLoading(false)
      }
    }
    fetch()
  }, [id, navigate])

  const handleChange = (setter) => (e) => {
    setter(e.target.value)
    setDirty(true)
  }

  const handleSave = async () => {
    if (!title.trim()) { toast.error('Title is required.'); return }
    setSaving(true)
    try {
      const { data } = await notesApi.update(id, {
        title: title.trim(),
        content,
      })
      setNote(data)
      setDirty(false)
      toast.success('Changes saved')
    } catch (err) {
      toast.error(extractError(err))
    } finally {
      setSaving(false)
    }
  }

  const handleKeyDown = (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') handleSave()
    if (e.key === 'Tab') {
      e.preventDefault()
      const el  = e.target
      const s   = el.selectionStart
      const val = el.value
      el.value  = val.slice(0, s) + '  ' + val.slice(el.selectionEnd)
      el.selectionStart = el.selectionEnd = s + 2
      setContent(el.value)
      setDirty(true)
    }
  }

  const wordCount = content.trim() ? content.trim().split(/\s+/).length : 0

  if (loading) {
    return (
      <AppShell>
        <div className="flex justify-center py-20">
          <Spinner size="lg" className="text-ink-faint" />
        </div>
      </AppShell>
    )
  }

  return (
    <AppShell>
      <div className="max-w-2xl mx-auto px-6 py-8 animate-fade-in">
        {/* Top bar */}
        <div className="flex items-center justify-between mb-6">
          <Link to={`/notes/${id}`} className="btn-ghost text-xs">
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            View note
          </Link>
          <div className="flex items-center gap-3">
            <span className="text-xs text-ink-muted">
              {dirty ? 'Unsaved changes' : `Saved ${fmtDateTime(note?.updated_at)}`}
            </span>
            {content && (
              <span className="text-xs text-ink-muted">{wordCount}w</span>
            )}
            <button
              onClick={handleSave}
              disabled={saving || !dirty}
              className="btn-primary"
            >
              {saving ? <><Spinner size="sm" /> Saving…</> : 'Save'}
            </button>
          </div>
        </div>

        {/* Title */}
        <input
          type="text"
          value={title}
          onChange={handleChange(setTitle)}
          onKeyDown={handleKeyDown}
          placeholder="Note title"
          className="w-full text-2xl font-semibold text-ink placeholder:text-ink-faint
                     bg-transparent border-none outline-none mb-4"
        />

        {/* Tags */}
        <div className="mb-4">
          <TagManager noteId={id} initialTags={note?.tags ?? []} />
        </div>

        <div className="border-t border-ink-faint mb-4" />

        {/* Monospace content editor */}
        <textarea
          value={content}
          onChange={handleChange(setContent)}
          onKeyDown={handleKeyDown}
          placeholder="Start writing…"
          className="note-editor min-h-[60vh]"
          spellCheck={false}
        />

        <p className="mt-4 text-xs text-ink-faint">⌘ Enter to save · Tab inserts two spaces</p>
      </div>
    </AppShell>
  )
}
