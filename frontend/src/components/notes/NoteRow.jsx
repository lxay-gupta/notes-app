import { Link } from 'react-router-dom'
import { fmtRelative, truncate } from '../../utils/helpers'

export function NoteRow({ note, onArchive, onDelete }) {
  const handleArchive = (e) => { e.preventDefault(); e.stopPropagation(); onArchive(note) }
  const handleDelete  = (e) => { e.preventDefault(); e.stopPropagation(); onDelete(note) }

  return (
    <Link
      to={`/notes/${note.id}`}
      className="group flex items-start gap-4 px-4 py-3 hover:bg-surface-muted rounded-lg transition-colors duration-100 animate-fade-in"
    >
      {/* Archived indicator */}
      <div className="mt-0.5 flex-shrink-0">
        {note.archived ? (
          <span title="Archived">
            <svg className="w-3.5 h-3.5 text-ink-faint" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8l1 12a2 2 0 002 2h8a2 2 0 002-2L19 8" />
            </svg>
          </span>
        ) : (
          <div className="w-1.5 h-1.5 rounded-full bg-accent mt-1.5" />
        )}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-baseline gap-2">
          <span className="text-sm font-medium text-ink truncate">{note.title}</span>
          <span className="text-xs text-ink-faint flex-shrink-0">{fmtRelative(note.updated_at)}</span>
        </div>
        {note.content && (
          <p className="mt-0.5 text-xs text-ink-muted font-mono leading-relaxed line-clamp-1">
            {truncate(note.content, 100)}
          </p>
        )}
        {note.tags?.length > 0 && (
          <div className="mt-1.5 flex flex-wrap gap-1">
            {note.tags.slice(0, 4).map(tag => (
              <span key={tag.id} className="tag-pill">{tag.name}</span>
            ))}
          </div>
        )}
      </div>

      {/* Row actions (visible on hover) */}
      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0 mt-0.5">
        <button
          onClick={handleArchive}
          className="p-1.5 text-ink-muted hover:text-ink rounded transition-colors"
          title={note.archived ? 'Unarchive' : 'Archive'}
          aria-label={note.archived ? 'Unarchive note' : 'Archive note'}
        >
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
              d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8l1 12a2 2 0 002 2h8a2 2 0 002-2L19 8" />
          </svg>
        </button>
        <button
          onClick={handleDelete}
          className="p-1.5 text-ink-muted hover:text-red-500 rounded transition-colors"
          title="Delete note"
          aria-label="Delete note"
        >
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
              d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
        </button>
      </div>
    </Link>
  )
}
