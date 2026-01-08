import { Routes, Route, Navigate } from 'react-router-dom';
import { authAPI } from './api/client';
import Login from './pages/Login';
import UserDashboard from './pages/UserDashboard';
import AnalystDashboard from './pages/AnalystDashboard';
import Alerts from './pages/Alerts';
import Reports from './pages/Reports';
import Layout from './components/Layout';

// Protected Route wrapper
function ProtectedRoute({ children, requiredRole }) {
  const isAuthenticated = authAPI.isAuthenticated();
  const user = authAPI.getStoredUser();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (requiredRole && user?.role !== requiredRole && user?.role !== 'ADMIN') {
    if (requiredRole === 'ANALYST' && user?.role === 'USER') {
      return <Navigate to="/dashboard" replace />;
    }
  }

  return children;
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        
        <Route path="dashboard" element={<UserDashboard />} />
        
        <Route
          path="analyst"
          element={
            <ProtectedRoute requiredRole="ANALYST">
              <AnalystDashboard />
            </ProtectedRoute>
          }
        />
        
        <Route
          path="alerts"
          element={
            <ProtectedRoute requiredRole="ANALYST">
              <Alerts />
            </ProtectedRoute>
          }
        />
        
        <Route
          path="reports"
          element={
            <ProtectedRoute requiredRole="ANALYST">
              <Reports />
            </ProtectedRoute>
          }
        />
      </Route>
      
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

export default App;
