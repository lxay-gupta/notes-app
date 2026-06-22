export function Pagination({ page, pages, onPageChange }) {
  if (pages <= 1) return null
  return (
    <div className="flex items-center justify-between mt-4 pt-4 border-t border-ink-faint">
      <button
        className="btn-ghost text-xs"
        onClick={() => onPageChange(page - 1)}
        disabled={page <= 1}
      >
        ← Previous
      </button>
      <span className="text-xs text-ink-muted">
        Page {page} of {pages}
      </span>
      <button
        className="btn-ghost text-xs"
        onClick={() => onPageChange(page + 1)}
        disabled={page >= pages}
      >
        Next →
      </button>
    </div>
  )
}
