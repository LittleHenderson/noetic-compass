import { lazy, Suspense } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { isAuthenticated } from './api/auth';
import { AppShell } from './components/layout/AppShell';
import { LoadingSpinner } from './components/shared/LoadingSpinner';
import type { ReactNode } from 'react';

/* Lazy-loaded pages — each becomes its own chunk */
const AssessmentPage = lazy(() => import('./pages/AssessmentPage').then(m => ({ default: m.AssessmentPage })));
const HistoryPage    = lazy(() => import('./pages/HistoryPage').then(m => ({ default: m.HistoryPage })));
const ConfigPage     = lazy(() => import('./pages/ConfigPage').then(m => ({ default: m.ConfigPage })));
const DetailsPage    = lazy(() => import('./pages/DetailsPage').then(m => ({ default: m.DetailsPage })));
const HowItWorksPage = lazy(() => import('./pages/HowItWorksPage').then(m => ({ default: m.HowItWorksPage })));
const FaqPage        = lazy(() => import('./pages/FaqPage').then(m => ({ default: m.FaqPage })));
const CohortPage     = lazy(() => import('./pages/CohortPage').then(m => ({ default: m.CohortPage })));
const LoginPage      = lazy(() => import('./pages/LoginPage').then(m => ({ default: m.LoginPage })));

function AuthGuard({ children }: { children: ReactNode }) {
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

export default function App() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center min-h-screen"><LoadingSpinner /></div>}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/*"
          element={
            <AuthGuard>
              <AppShell>
                <Suspense fallback={<LoadingSpinner />}>
                  <Routes>
                    <Route path="/" element={<AssessmentPage />} />
                    <Route path="/history" element={<HistoryPage />} />
                    <Route path="/config" element={<ConfigPage />} />
                    <Route path="/details/:id" element={<DetailsPage />} />
                    <Route path="/cohort" element={<CohortPage />} />
                    <Route path="/how-it-works" element={<HowItWorksPage />} />
                    <Route path="/faq" element={<FaqPage />} />
                  </Routes>
                </Suspense>
              </AppShell>
            </AuthGuard>
          }
        />
      </Routes>
    </Suspense>
  );
}
