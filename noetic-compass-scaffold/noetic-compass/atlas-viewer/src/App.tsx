import { Navigate, Route, Routes } from 'react-router-dom';
import type { ReactNode } from 'react';
import LoginPage from './pages/LoginPage';
import LicensePage from './pages/LicensePage';
import ModelConfigPage from './pages/ModelConfigPage';
import CockpitPage from './pages/CockpitPage';

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
            <CockpitPage />
          </AuthGate>
        }
      />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}
