import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import {
  clearStoredAccountSession,
  loginOrRedeemAccount,
  logoutAccountSession,
  readStoredAccountSession,
  writeStoredAccountSession,
  type AccountSession,
} from '../../lib/accountAuth';

export interface AccountLoginFormInput {
  email: string;
  inviteCode?: string | null;
  displayName?: string | null;
}

interface AccountAuthContextValue {
  session: AccountSession | null;
  login: (input: AccountLoginFormInput) => Promise<AccountSession>;
  logout: () => Promise<void>;
}

const AccountAuthContext = createContext<AccountAuthContextValue | null>(null);

export function AccountAuthProvider({ children }: { children: ReactNode }): JSX.Element {
  const [session, setSession] = useState<AccountSession | null>(() => readStoredAccountSession());

  const login = useCallback(async (input: AccountLoginFormInput): Promise<AccountSession> => {
    const next = await loginOrRedeemAccount(input);
    writeStoredAccountSession(next);
    setSession(next);
    return next;
  }, []);

  const logout = useCallback(async (): Promise<void> => {
    const token = session?.token ?? null;
    try {
      if (token) {
        await logoutAccountSession(token);
      }
    } catch {
      // Local post-condition is the same even if the server already rejected the token.
    } finally {
      clearStoredAccountSession();
      setSession(null);
    }
  }, [session?.token]);

  const value = useMemo(
    () => ({
      session,
      login,
      logout,
    }),
    [login, logout, session],
  );

  return (
    <AccountAuthContext.Provider value={value}>
      {children}
    </AccountAuthContext.Provider>
  );
}

export function useAccountAuth(): AccountAuthContextValue {
  const value = useContext(AccountAuthContext);
  if (!value) {
    throw new Error('useAccountAuth must be used inside AccountAuthProvider.');
  }
  return value;
}
