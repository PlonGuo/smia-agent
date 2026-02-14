import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import {
  Toaster,
  ToastRoot,
  ToastTitle,
  ToastDescription,
  ToastCloseTrigger,
  ToastIndicator,
} from '@chakra-ui/react';
import { toaster } from './lib/toaster';
import { useAuth } from './hooks/useAuth';
import Home from './pages/Home';
import Login from './pages/Login';
import Signup from './pages/Signup';
import Analyze from './pages/Analyze';
import Dashboard from './pages/Dashboard';
import ReportDetail from './pages/ReportDetail';
import Settings from './pages/Settings';
import Layout from './components/Layout';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();

  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route
          path="/analyze"
          element={
            <ProtectedRoute>
              <Layout>
                <Analyze />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <Layout>
                <Dashboard />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/reports/:id"
          element={
            <ProtectedRoute>
              <Layout>
                <ReportDetail />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/settings"
          element={
            <ProtectedRoute>
              <Layout>
                <Settings />
              </Layout>
            </ProtectedRoute>
          }
        />
      </Routes>
      <Toaster toaster={toaster}>
        {(toast) => (
          <ToastRoot>
            <ToastIndicator />
            <ToastTitle>{toast.title}</ToastTitle>
            <ToastDescription>{toast.description}</ToastDescription>
            <ToastCloseTrigger />
          </ToastRoot>
        )}
      </Toaster>
    </BrowserRouter>
  );
}

export default App;
