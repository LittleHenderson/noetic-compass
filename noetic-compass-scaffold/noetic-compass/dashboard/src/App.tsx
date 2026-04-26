import { lazy, Suspense } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { isAuthenticated } from './api/auth';
import { AppShell } from './components/layout/AppShell';
import { LoadingSpinner } from './components/shared/LoadingSpinner';
import { InstallBanner } from './components/shared/InstallBanner';
import type { ReactNode } from 'react';

/* Lazy-loaded pages — each becomes its own chunk */
const AssessmentPage = lazy(() => import('./pages/AssessmentPage').then(m => ({ default: m.AssessmentPage })));
const HistoryPage    = lazy(() => import('./pages/HistoryPage').then(m => ({ default: m.HistoryPage })));
const ConfigPage     = lazy(() => import('./pages/ConfigPage').then(m => ({ default: m.ConfigPage })));
const DetailsPage    = lazy(() => import('./pages/DetailsPage').then(m => ({ default: m.DetailsPage })));
const HowItWorksPage = lazy(() => import('./pages/HowItWorksPage').then(m => ({ default: m.HowItWorksPage })));
const FaqPage        = lazy(() => import('./pages/FaqPage').then(m => ({ default: m.FaqPage })));
const CohortPage     = lazy(() => import('./pages/CohortPage').then(m => ({ default: m.CohortPage })));
const AiChallengesPage = lazy(() => import('./pages/AiChallengesPage').then(m => ({ default: m.AiChallengesPage })));
const ScenarioBrowserPage = lazy(() => import('./pages/ScenarioBrowserPage').then(m => ({ default: m.ScenarioBrowserPage })));
const ValidationPage = lazy(() => import('./pages/ValidationPage').then(m => ({ default: m.ValidationPage })));
const ValidationLeaderboardPage = lazy(() => import('./pages/ValidationLeaderboardPage').then(m => ({ default: m.ValidationLeaderboardPage })));
const ReproducibilityPage = lazy(() => import('./pages/ReproducibilityPage').then(m => ({ default: m.ReproducibilityPage })));
const CompilerPage = lazy(() => import('./pages/CompilerPage').then(m => ({ default: m.CompilerPage })));
const ForecastPage = lazy(() => import('./pages/ForecastPage').then(m => ({ default: m.ForecastPage })));
const VisualizationPage = lazy(() => import('./pages/VisualizationPage').then(m => ({ default: m.VisualizationPage })));
const TutorialPage = lazy(() => import('./pages/TutorialPage').then(m => ({ default: m.TutorialPage })));
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
      <InstallBanner />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/*"
          element={
            <AuthGuard>
              <AppShell>
                <Suspense fallback={<LoadingSpinner />}>
                  <Routes>
                    <Route path="/" element={<Navigate to="/scenarios" replace />} />
                    <Route path="/assessment" element={<AssessmentPage />} />
                    <Route path="/history" element={<HistoryPage />} />
                    <Route path="/config" element={<ConfigPage />} />
                    <Route path="/details/:id" element={<DetailsPage />} />
                    <Route path="/cohort" element={<CohortPage />} />
                    {/* /benchmark merged into /assessment (mode toggle) — keep a redirect for old bookmarks */}
                    <Route path="/benchmark" element={<Navigate to="/assessment" replace />} />
                    <Route path="/scenarios" element={<ScenarioBrowserPage />} />
                    <Route path="/validate" element={<ValidationPage />} />
                    <Route path="/validation/leaderboard" element={<ValidationLeaderboardPage />} />
                    <Route path="/reproducibility" element={<ReproducibilityPage />} />
                    <Route path="/compiler" element={<CompilerPage />} />
                    <Route path="/forecast" element={<ForecastPage />} />
                    <Route path="/visualization" element={<VisualizationPage />} />
                    <Route path="/tutorial" element={<TutorialPage />} />
                    <Route path="/ai-challenges" element={<AiChallengesPage />} />
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
