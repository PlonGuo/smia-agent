import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import {
  Box,
  Spinner,
  Text,
  Toaster,
  ToastRoot,
  ToastTitle,
  ToastDescription,
  ToastCloseTrigger,
  ToastIndicator,
} from '@chakra-ui/react';
import { toaster } from './lib/toaster';
import { useAuth } from './hooks/useAuth';
import ErrorBoundary from './components/ErrorBoundary';
import Layout from './components/Layout';

// Lazy-loaded pages for better bundle splitting
const Home = lazy(() => import('./pages/Home'));
const Login = lazy(() => import('./pages/Login'));
const Signup = lazy(() => import('./pages/Signup'));
const Analyze = lazy(() => import('./pages/Analyze'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const ReportDetail = lazy(() => import('./pages/ReportDetail'));
const Settings = lazy(() => import('./pages/Settings'));

function PageLoader() {
  return (
    <Box py={20} textAlign="center">
      <Spinner size="lg" />
      <Text mt={3} color="fg.muted" fontSize="sm">
        Loading...
      </Text>
    </Box>
  );
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();

  if (loading) return <PageLoader />;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function App() {
  return (
    <BrowserRouter>
      <ErrorBoundary>
        <Suspense fallback={<PageLoader />}>
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
        </Suspense>
      </ErrorBoundary>
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
