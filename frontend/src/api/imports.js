import api from './client'

export const importsApi = {
  upload: (file) => {
    const form = new FormData()
    form.append('file', file)
    return api.post('/imports/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  history: (params = {}) =>
    api.get('/imports/history', { params }),
}
