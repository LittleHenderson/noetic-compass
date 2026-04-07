import { Routes, Route, Navigate } from 'react-router-dom';
import { isAuthenticated } from './api/auth';
import { AppShell } from './components/layout/AppShell';
import { AssessmentPage } from './pages/AssessmentPage';
import { HistoryPage } from './pages/HistoryPage';
import { ConfigPage } from './pages/ConfigPage';
import { DetailsPage } from './pages/DetailsPage';
import { HowItWorksPage } from './pages/HowItWorksPage';
import { FaqPage } from './pages/FaqPage';
import { CohortPage } from './pages/CohortPage';
import { LoginPage } from './pages/LoginPage';
import type { ReactNode } from 'react';

function AuthGuard({ children }: { children: ReactNode }) {
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/*"
        element={
          <AuthGuard>
            <AppShell>
              <Routes>
                <Route path="/" element={<AssessmentPage />} />
                <Route path="/history" element={<HistoryPage />} />
                <Route path="/config" element={<ConfigPage />} />
                <Route path="/details/:id" element={<DetailsPage />} />
                <Route path="/cohort" element={<CohortPage />} />
                <Route path="/how-it-works" element={<HowItWorksPage />} />
                <Route path="/faq" element={<FaqPage />} />
              </Routes>
            </AppShell>
          </AuthGuard>
        }
      />
    </Routes>
  );
}
