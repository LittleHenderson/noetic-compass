// CAS Forex feature router. Mounted at /forex/* by App.tsx. The shell provides
// the backdrop + nav; only the Proof Center is wired in Phase 1.

import { Navigate, Route, Routes } from 'react-router-dom';
import { ForexShell } from './components/ForexShell';
import { ForexProofPage } from './pages/ForexProofPage';

export default function ForexApp() {
  return (
    <ForexShell>
      <Routes>
        <Route index element={<Navigate to="proof" replace />} />
        <Route path="proof" element={<ForexProofPage />} />
        <Route path="*" element={<Navigate to="proof" replace />} />
      </Routes>
    </ForexShell>
  );
}
