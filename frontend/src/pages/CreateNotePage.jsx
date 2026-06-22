import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { notesApi } from '../api/notes'
import { AppShell } from '../components/layout/AppShell'
import { Spinner } from '../components/ui/Spinner'
import { extractError } from '../utils/helpers'
import toast from 'react-hot-toast'

export function CreateNotePage() {
  const navigate = useNavigate()
  const [title,   setTitle]   = useState('')
  const [content, setContent] = useState('')
  const [saving,  setSaving]  = useState(false)

  const handleSave = async (e) => {
    e?.preventDefault()
    if (!title.trim()) { toast.error('Title is required.'); return }
    setSaving(true)
    try {
      const { data } = await notesApi.create(title.trim(), content)
      toast.success('Note saved')
      navigate(`/notes/${data.id}`)
    } catch (err) {
      toast.error(extractError(err))
      setSaving(false)
    }
  }

  // Cmd/Ctrl+Enter saves
  const handleKeyDown = (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') handleSave()
  }

  const wordCount = content.trim() ? content.trim().split(/\s+/).length : 0

  return (
    <AppShell>
      <div className="max-w-2xl mx-auto px-6 py-8">
        {/* Top bar */}
        <div className="flex items-center justify-between mb-6">
          <Link to="/dashboard" className="btn-ghost text-xs">
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Cancel
          </Link>
          <div className="flex items-center gap-3">
            {content && (
              <span className="text-xs text-ink-muted">{wordCount} word{wordCount !== 1 ? 's' : ''}</span>
            )}
            <button
              onClick={handleSave}
              disabled={saving || !title.trim()}
              className="btn-primary"
            >
              {saving ? <><Spinner size="sm" /> Saving…</> : 'Save note'}
            </button>
          </div>
        </div>

        {/* Title */}
        <input
          type="text"
          value={title}
          onChange={e => setTitle(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Note title"
          autoFocus
          className="w-full text-2xl font-semibold text-ink placeholder:text-ink-faint
                     bg-transparent border-none outline-none mb-4 resize-none"
        />

        <div className="border-t border-ink-faint mb-4" />

        {/* Content — the monospace typewriter editor */}
        <div className="relative">
          <textarea
            value={content}
            onChange={e => setContent(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={"Start writing…\n\nTip: ⌘Enter to save"}
            className="note-editor min-h-[60vh]"
            spellCheck={false}
          />
        </div>

        <p className="mt-4 text-xs text-ink-faint">
          ⌘ Enter to save · <kbd className="font-mono">tab</kbd> inserts two spaces
        </p>
      </div>
    </AppShell>
  )
}
