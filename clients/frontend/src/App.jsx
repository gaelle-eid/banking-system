import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import AccountDetail from './pages/AccountDetail'
import Loans from './pages/Loans'
import Assistant from './pages/Assistant'
import Cards from './pages/Cards'

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
         
         <Route path="/assistant" element={<ProtectedRoute><Assistant /></ProtectedRoute>} /><Route path="/loans" element={<ProtectedRoute><Loans /></ProtectedRoute>} />
<Route path="/cards" element={<ProtectedRoute><Cards /></ProtectedRoute>} />
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
    </BrowserRouter>
  )
}