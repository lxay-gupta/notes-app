import api from './client'

export const authApi = {
  register: (email, password, fullName) =>
    api.post('/auth/register', { email, password, full_name: fullName }),

  login: (email, password) =>
    api.post('/auth/login', { email, password }),

  logout: (refreshToken) =>
    api.post('/auth/logout', { refresh_token: refreshToken }),

  me: () =>
    api.get('/auth/me'),
}
