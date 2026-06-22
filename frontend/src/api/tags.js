import api from './client'

export const tagsApi = {
  list: () =>
    api.get('/tags'),

  create: (name) =>
    api.post('/tags', { name }),

  delete: (id) =>
    api.delete(`/tags/${id}`),

  listForNote: (noteId) =>
    api.get(`/tags/note/${noteId}`),

  attach: (noteId, tagId) =>
    api.post(`/tags/note/${noteId}`, { tag_id: tagId }),

  detach: (noteId, tagId) =>
    api.delete(`/tags/note/${noteId}/${tagId}`),
}
