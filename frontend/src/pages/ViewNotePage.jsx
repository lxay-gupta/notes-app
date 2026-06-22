import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { notesApi } from '../api/notes'
import { AppShell } from '../components/layout/AppShell'
import { TagManager } from '../components/tags/TagManager'
import { ConfirmDialog } from '../components/ui/ConfirmDialog'
import { Spinner } from '../components/ui/Spinner'
import { fmtDateTime } from '../utils/helpers'
import { extractError } from '../utils/helpers'
import toast from 'react-hot-toast'

export function ViewNotePage() {
  const { id }  = useParams()
  const navigate = useNavigate()

  const [note,     setNote]     = useState(null)
  const [loading,  setLoading]  = useState(true)
  const [deleting, setDeleting] = useState(false)
  const [showDel,  setShowDel]  = useState(false)

  useEffect(() => {
    const fetch = async () => {
      try {
        const { data } = await notesApi.get(id)
        setNote(data)
      } catch (err) {
        toast.error(extractError(err))
        navigate('/dashboard')
      } finally {
        setLoading(false)
      }
    }
    fetch()
  }, [id, navigate])

  const handleArchive = async () => {
    try {
      const { data } = await (note.archived ? notesApi.unarchive(id) : notesApi.archive(id))
      setNote(data)
      toast.success(note.archived ? 'Unarchived' : 'Archived')
    } catch (err) {
      toast.error(extractError(err))
    }
  }

  const handleDelete = async () => {
    setDeleting(true)
    try {
      await notesApi.delete(id)
      toast.success('Note deleted')
      navigate('/dashboard')
    } catch (err) {
      toast.error(extractError(err))
      setDeleting(false)
    }
  }

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
          <Link to="/dashboard" className="btn-ghost text-xs">
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            All notes
          </Link>
          <div className="flex items-center gap-2">
            {note.archived && (
              <span className="text-xs text-ink-muted bg-surface-muted px-2 py-1 rounded-md">Archived</span>
            )}
            <button onClick={handleArchive} className="btn-ghost text-xs">
              {note.archived ? 'Unarchive' : 'Archive'}
            </button>
            <Link to={`/notes/${id}/edit`} className="btn-primary text-xs">
              Edit
            </Link>
            <button onClick={() => setShowDel(true)} className="btn-ghost text-xs text-red-500 hover:text-red-600">
              Delete
            </button>
          </div>
        </div>

        {/* Title */}
        <h1 className="text-2xl font-semibold text-ink leading-snug mb-2">{note.title}</h1>

        {/* Meta */}
        <div className="flex items-center gap-3 mb-4 text-xs text-ink-muted">
          <span>Created {fmtDateTime(note.created_at)}</span>
          {note.updated_at !== note.created_at && (
            <span>· Updated {fmtDateTime(note.updated_at)}</span>
          )}
        </div>

        {/* Tags */}
        <div className="mb-6">
          <TagManager noteId={id} initialTags={note.tags ?? []} />
        </div>

        {/* Divider */}
        <div className="border-t border-ink-faint mb-6" />

        {/* Content — monospace, the signature element */}
        {note.content ? (
          <pre className="font-mono text-sm leading-relaxed text-ink whitespace-pre-wrap break-words">
            {note.content}
          </pre>
        ) : (
          <p className="text-sm text-ink-muted italic">This note has no content.</p>
        )}
      </div>

      <ConfirmDialog
        open={showDel}
        onClose={() => setShowDel(false)}
        onConfirm={handleDelete}
        title="Delete note"
        message={`"${note?.title}" will be deleted. This can't be undone.`}
        confirmLabel="Delete note"
        loading={deleting}
      />
    </AppShell>
  )
}
