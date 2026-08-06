import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
import { ToastProvider } from './context/ToastContext'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import AccountDetail from './pages/AccountDetail'
import Loans from './pages/Loans'
import Assistant from './pages/Assistant'
import Cards from './pages/Cards'
import VerifyEmail from './pages/VerifyEmail'
import Statements from './pages/Statements'
import Profile from './pages/Profile'

export default function App() {
  return (
    <BrowserRouter>
      <ToastProvider>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/verify-email" element={<VerifyEmail />} />
          <Route path="/assistant" element={<ProtectedRoute><Assistant /></ProtectedRoute>} />
          <Route path="/loans" element={<ProtectedRoute><Loans /></ProtectedRoute>} />
          <Route path="/cards" element={<ProtectedRoute><Cards /></ProtectedRoute>} />
          <Route path="/statements" element={<ProtectedRoute><Statements /></ProtectedRoute>} />
          <Route path="/profile" element={<ProtectedRoute><Profile /></ProtectedRoute>} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/accounts/:id"
            element={
              <ProtectedRoute>
                <AccountDetail />
              </ProtectedRoute>
            }
          />
        </Routes>
      </AuthProvider>
      </ToastProvider>
    </BrowserRouter>
  )
}