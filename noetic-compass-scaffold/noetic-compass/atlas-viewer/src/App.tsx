import { lazy, Suspense } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import type { ReactNode } from 'react';
import LoginPage from './pages/LoginPage';
import LicensePage from './pages/LicensePage';
import ModelConfigPage from './pages/ModelConfigPage';

// CockpitPage pulls in Three.js (~500 KB). Lazy-load it so the initial bundle
// stays small for the eager Login / License / ModelConfig routes.
const CockpitPage = lazy(() => import('./pages/CockpitPage'));

function AuthGate({ children }: { children: ReactNode }) {
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/license"
        element={
          <AuthGate>
            <LicensePage />
          </AuthGate>
        }
      />
      <Route
        path="/model-config"
        element={
          <AuthGate>
            <ModelConfigPage />
          </AuthGate>
        }
      />
      <Route
        path="/cockpit"
        element={
          <AuthGate>
            <Suspense fallback={<div>Loading cockpit…</div>}>
              <CockpitPage />
            </Suspense>
          </AuthGate>
        }
      />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}
