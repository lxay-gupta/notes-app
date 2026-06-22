import { useCallback, useEffect, useState } from 'react'
import { tagsApi } from '../../api/tags'
import { extractError } from '../../utils/helpers'
import toast from 'react-hot-toast'

export function TagManager({ noteId, initialTags = [] }) {
  const [allTags, setAllTags]       = useState([])
  const [noteTags, setNoteTags]     = useState(initialTags)
  const [newTagName, setNewTagName] = useState('')
  const [creating, setCreating]     = useState(false)
  const [open, setOpen]             = useState(false)

  const fetchAll = useCallback(async () => {
    try {
      const { data } = await tagsApi.list()
      setAllTags(data)
    } catch { /* silent */ }
  }, [])

  useEffect(() => { fetchAll() }, [fetchAll])

  const isAttached = (tagId) => noteTags.some(t => t.id === tagId)

  const toggleTag = async (tag) => {
    try {
      if (isAttached(tag.id)) {
        const { data } = await tagsApi.detach(noteId, tag.id)
        setNoteTags(data)
        toast.success(`Removed "${tag.name}"`)
      } else {
        const { data } = await tagsApi.attach(noteId, tag.id)
        setNoteTags(data)
        toast.success(`Added "${tag.name}"`)
      }
    } catch (err) {
      toast.error(extractError(err))
    }
  }

  const createTag = async (e) => {
    e.preventDefault()
    if (!newTagName.trim()) return
    setCreating(true)
    try {
      const { data: tag } = await tagsApi.create(newTagName.trim())
      setAllTags(prev => [...prev, tag])
      // Auto-attach the new tag
      const { data: updated } = await tagsApi.attach(noteId, tag.id)
      setNoteTags(updated)
      setNewTagName('')
      toast.success(`Tag "${tag.name}" created and attached`)
    } catch (err) {
      toast.error(extractError(err))
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="relative">
      {/* Attached tags + toggle */}
      <div className="flex flex-wrap items-center gap-1.5">
        {noteTags.map(tag => (
          <button
            key={tag.id}
            onClick={() => toggleTag(tag)}
            className="tag-pill group"
            title={`Remove "${tag.name}"`}
          >
            {tag.name}
            <svg className="w-3 h-3 opacity-50 group-hover:opacity-100" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        ))}
        <button
          onClick={() => setOpen(v => !v)}
          className="inline-flex items-center gap-1 px-2 py-0.5 border border-dashed border-ink-faint
                     text-xs text-ink-muted rounded-full hover:border-accent hover:text-accent transition-colors"
        >
          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Tag
        </button>
      </div>

      {/* Tag picker dropdown */}
      {open && (
        <div className="absolute top-full left-0 mt-1 w-56 bg-white border border-ink-faint rounded-lg
                        shadow-lg z-20 animate-slide-in">
          <div className="p-2 border-b border-ink-faint">
            <form onSubmit={createTag} className="flex gap-1">
              <input
                type="text"
                value={newTagName}
                onChange={e => setNewTagName(e.target.value)}
                placeholder="New tag…"
                className="input text-xs py-1 px-2 flex-1"
                disabled={creating}
                autoFocus
              />
              <button
                type="submit"
                disabled={creating || !newTagName.trim()}
                className="btn-primary text-xs py-1 px-2"
              >
                Add
              </button>
            </form>
          </div>
          <ul className="max-h-40 overflow-y-auto py-1">
            {allTags.length === 0 && (
              <li className="px-3 py-2 text-xs text-ink-muted">No tags yet — create one above.</li>
            )}
            {allTags.map(tag => (
              <li key={tag.id}>
                <button
                  onClick={() => toggleTag(tag)}
                  className="w-full flex items-center justify-between px-3 py-1.5
                             text-xs text-ink hover:bg-surface-muted transition-colors"
                >
                  <span>{tag.name}</span>
                  {isAttached(tag.id) && (
                    <svg className="w-3 h-3 text-accent" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  )}
                </button>
              </li>
            ))}
          </ul>
          <div className="p-2 border-t border-ink-faint">
            <button
              onClick={() => setOpen(false)}
              className="w-full text-xs text-ink-muted hover:text-ink text-center py-1 transition-colors"
            >
              Done
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
