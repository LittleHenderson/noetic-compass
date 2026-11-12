import { lazy, Suspense } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { LoadingSpinner } from './components/shared/LoadingSpinner';

const HowItWorksPage = lazy(() => import('./pages/HowItWorksPage').then(m => ({ default: m.HowItWorksPage })));
const FaqPage = lazy(() => import('./pages/FaqPage').then(m => ({ default: m.FaqPage })));
const LoginPage = lazy(() => import('./pages/LoginPage').then(m => ({ default: m.LoginPage })));

export default function App() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/how-it-works" element={<HowItWorksPage />} />
        <Route path="/faq" element={<FaqPage />} />
        {/* Retired private routes cannot be reopened by a cached legacy JWT. */}
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </Suspense>
  );
}
