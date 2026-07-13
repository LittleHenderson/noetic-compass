import type { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAccountAuth } from '../../auth/AccountAuthProvider';

export interface AuthGateProps {
  children: ReactNode;
}

export function AuthGate({ children }: AuthGateProps): JSX.Element {
  const { accountsEnabled, isAuthenticated } = useAccountAuth();
  const location = useLocation();

  if (accountsEnabled && !isAuthenticated) {
    return (
      <Navigate
        to="/login"
        replace
        state={{ from: `${location.pathname}${location.search}${location.hash}` }}
      />
    );
  }
  return <>{children}</>;
}

export default AuthGate;
