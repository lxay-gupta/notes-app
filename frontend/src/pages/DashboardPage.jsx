import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { notesApi } from '../api/notes'
import { AppShell } from '../components/layout/AppShell'
import { NoteRow } from '../components/notes/NoteRow'
import { SearchBar } from '../components/ui/SearchBar'
import { Spinner } from '../components/ui/Spinner'
import { Empty } from '../components/ui/Empty'
import { Pagination } from '../components/ui/Pagination'
import { ConfirmDialog } from '../components/ui/ConfirmDialog'
import { extractError } from '../utils/helpers'
import toast from 'react-hot-toast'

const FILTERS = [
  { label: 'All',      value: undefined },
  { label: 'Active',   value: false },
  { label: 'Archived', value: true },
]

export function DashboardPage() {
  const [notes,      setNotes]      = useState([])
  const [total,      setTotal]      = useState(0)
  const [pages,      setPages]      = useState(0)
  const [page,       setPage]       = useState(1)
  const [loading,    setLoading]    = useState(true)
  const [query,      setQuery]      = useState('')
  const [archived,   setArchived]   = useState(undefined)
  const [toDelete,   setToDelete]   = useState(null)
  const [deleting,   setDeleting]   = useState(false)

  const PAGE_SIZE = 20

  const fetchNotes = useCallback(async () => {
    setLoading(true)
    try {
      let res
      if (query) {
        res = await notesApi.search(query, { page, page_size: PAGE_SIZE })
      } else {
        res = await notesApi.list({ page, page_size: PAGE_SIZE, archived })
      }
      setNotes(res.data.items)
      setTotal(res.data.total)
      setPages(res.data.pages)
    } catch (err) {
      toast.error(extractError(err))
    } finally {
      setLoading(false)
    }
  }, [query, page, archived])

  useEffect(() => { fetchNotes() }, [fetchNotes])

  // Reset to page 1 whenever search or filter changes
  useEffect(() => { setPage(1) }, [query, archived])

  const handleSearch = useCallback((q) => setQuery(q), [])

  const handleArchive = async (note) => {
    try {
      await (note.archived ? notesApi.unarchive(note.id) : notesApi.archive(note.id))
      toast.success(note.archived ? 'Unarchived' : 'Archived')
      fetchNotes()
    } catch (err) {
      toast.error(extractError(err))
    }
  }

  const confirmDelete = (note) => setToDelete(note)

  const handleDelete = async () => {
    if (!toDelete) return
    setDeleting(true)
    try {
      await notesApi.delete(toDelete.id)
      toast.success('Note deleted')
      setToDelete(null)
      fetchNotes()
    } catch (err) {
      toast.error(extractError(err))
    } finally {
      setDeleting(false)
    }
  }

  return (
    <AppShell>
      <div className="max-w-3xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-lg font-semibold text-ink">Notes</h1>
            <p className="text-xs text-ink-muted mt-0.5">
              {total > 0 ? `${total} note${total !== 1 ? 's' : ''}` : 'Nothing here yet'}
            </p>
          </div>
          <Link to="/notes/new" className="btn-primary">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            New note
          </Link>
        </div>

        {/* Controls */}
        <div className="flex items-center gap-3 mb-4">
          <SearchBar onSearch={handleSearch} className="flex-1" />
          {!query && (
            <div className="flex items-center gap-0.5 bg-surface-muted rounded-lg p-0.5 flex-shrink-0">
              {FILTERS.map(f => (
                <button
                  key={String(f.value)}
                  onClick={() => setArchived(f.value)}
                  className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                    archived === f.value
                      ? 'bg-white text-ink shadow-sm'
                      : 'text-ink-muted hover:text-ink'
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* List */}
        {loading ? (
          <div className="flex justify-center py-16">
            <Spinner size="lg" className="text-ink-faint" />
          </div>
        ) : notes.length === 0 ? (
          <Empty
            icon={
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            }
            title={query ? `No notes match "${query}"` : 'No notes yet'}
            description={query ? 'Try a different search term.' : 'Create your first note to get started.'}
            action={
              !query && (
                <Link to="/notes/new" className="btn-primary">
                  New note
                </Link>
              )
            }
          />
        ) : (
          <div className="space-y-0.5">
            {notes.map(note => (
              <NoteRow
                key={note.id}
                note={note}
                onArchive={handleArchive}
                onDelete={confirmDelete}
              />
            ))}
          </div>
        )}

        <Pagination page={page} pages={pages} onPageChange={setPage} />
      </div>

      <ConfirmDialog
        open={!!toDelete}
        onClose={() => setToDelete(null)}
        onConfirm={handleDelete}
        title="Delete note"
        message={`"${toDelete?.title}" will be moved to trash. This can't be undone.`}
        confirmLabel="Delete note"
        loading={deleting}
      />
    </AppShell>
  )
}
