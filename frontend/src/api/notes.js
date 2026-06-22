import api from './client'

export const notesApi = {
  list: (params = {}) =>
    api.get('/notes', { params }),

  search: (q, params = {}) =>
    api.get('/notes/search', { params: { q, ...params } }),

  get: (id) =>
    api.get(`/notes/${id}`),

  create: (title, content = '') =>
    api.post('/notes', { title, content }),

  update: (id, data) =>
    api.patch(`/notes/${id}`, data),

  delete: (id) =>
    api.delete(`/notes/${id}`),

  archive: (id) =>
    api.post(`/notes/${id}/archive`),

  unarchive: (id) =>
    api.post(`/notes/${id}/unarchive`),
}
