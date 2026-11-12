import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { clearToken } from '../api/auth';
import { BrandTagline } from '../components/shared/BrandTagline';
import { PatentPendingBadge } from '../components/shared/PatentPendingBadge';

/** The legacy dashboard is not compatible with the account API allowlist. */
export function LoginPage() {
  useEffect(() => { clearToken(); }, []);
  return (
    <div className="flex min-h-screen items-center justify-center bg-dark-900 px-4">
      <div className="glass-card w-full max-w-md p-8">
        <PatentPendingBadge className="mb-4" />
        <h1 className="text-2xl font-bold">Noetic Compass</h1>
        <BrandTagline variant="hero" align="center" />
        <p role="status" className="mt-6">Legacy dashboard sign-in is retired.</p>
        <p className="mt-3 text-sm text-slate-400">
          Customer access requires the account-enabled Atlas application and your own private
          account credential. Contact the platform operator for the verified account application
          address. Username-only access is unavailable.
        </p>
        <p className="mt-3 text-sm text-slate-400">
          Legacy assessment, history, scenarios, and other dashboard tools are not supported
          by this account release. No automatic identity or quota reset is available.
        </p>
        <nav aria-label="Public information" className="mt-6 flex gap-4">
          <Link to="/how-it-works">How it works</Link>
          <Link to="/faq">FAQ</Link>
        </nav>
      </div>
    </div>
  );
}
