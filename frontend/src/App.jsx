import { Navigate, Route, Routes } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { AuthProvider } from './context/AuthContext'
import { ProtectedRoute } from './components/layout/ProtectedRoute'
import { LoginPage }      from './pages/LoginPage'
import { RegisterPage }   from './pages/RegisterPage'
import { DashboardPage }  from './pages/DashboardPage'
import { CreateNotePage } from './pages/CreateNotePage'
import { EditNotePage }   from './pages/EditNotePage'
import { ViewNotePage }   from './pages/ViewNotePage'
import { ImportPage }     from './pages/ImportPage'

export default function App() {
  return (
    <AuthProvider>
      <Toaster
        position="bottom-right"
        toastOptions={{
          duration: 3000,
          style: {
            background: '#0F172A',
            color: '#F8FAFC',
            fontSize: '13px',
            borderRadius: '8px',
          },
          success: { iconTheme: { primary: '#F59E0B', secondary: '#0F172A' } },
        }}
      />
      <Routes>
        {/* Public */}
        <Route path="/login"    element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        {/* Protected */}
        <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
        <Route path="/notes/new" element={<ProtectedRoute><CreateNotePage /></ProtectedRoute>} />
        <Route path="/notes/:id" element={<ProtectedRoute><ViewNotePage /></ProtectedRoute>} />
        <Route path="/notes/:id/edit" element={<ProtectedRoute><EditNotePage /></ProtectedRoute>} />
        <Route path="/import"    element={<ProtectedRoute><ImportPage /></ProtectedRoute>} />

        {/* Redirects */}
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </AuthProvider>
  )
}
