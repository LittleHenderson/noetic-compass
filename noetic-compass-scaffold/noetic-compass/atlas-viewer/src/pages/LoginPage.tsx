import { useEffect, useState, type CSSProperties, type FormEvent } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAccountAuth } from '../auth/AccountAuthProvider';
import { GlassPanel } from '../components/ui/GlassPanel';
import { PageShell } from '../components/ui/PageShell';
import { generateAccountCredential } from '../lib/accountAuthApi';
import { ACCENT_TEAL, COLORS, THEME } from '../lib/designTokens';

type LoginMode = 'sign-in' | 'redeem';

const headingStyle: CSSProperties = {
  margin: 0,
  fontSize: 24,
  fontWeight: 800,
  color: COLORS.textPrimary,
};

const textStyle: CSSProperties = {
  margin: '8px 0 18px',
  fontSize: 13,
  lineHeight: 1.55,
  color: COLORS.textSecondary,
};

const fieldStyle: CSSProperties = {
  display: 'grid',
  gap: 6,
  marginBottom: 12,
};

const labelStyle: CSSProperties = {
  color: COLORS.textMuted,
  fontSize: 10.5,
  fontWeight: 700,
  letterSpacing: 0.8,
  textTransform: 'uppercase',
};

const inputStyle: CSSProperties = {
  width: '100%',
  padding: '10px 12px',
  borderRadius: 6,
  border: '1px solid rgba(255,255,255,0.10)',
  background: 'rgba(255,255,255,0.03)',
  color: COLORS.textPrimary,
  fontFamily: THEME.fontFamily,
  fontSize: 14,
};

const buttonStyle = (primary = false, disabled = false): CSSProperties => ({
  minHeight: 38,
  padding: '8px 13px',
  borderRadius: 6,
  border: primary
    ? `1px solid ${ACCENT_TEAL}`
    : '1px solid rgba(255,255,255,0.12)',
  background: primary ? 'rgba(45,212,191,0.10)' : 'rgba(255,255,255,0.03)',
  color: primary ? ACCENT_TEAL : COLORS.textSecondary,
  cursor: disabled ? 'not-allowed' : 'pointer',
  opacity: disabled ? 0.5 : 1,
  fontFamily: THEME.fontFamily,
  fontSize: 12.5,
  fontWeight: 700,
});

const credentialStyle: CSSProperties = {
  display: 'block',
  padding: 12,
  borderRadius: 6,
  border: '1px solid rgba(251,191,36,0.30)',
  background: 'rgba(251,191,36,0.06)',
  color: '#fef3c7',
  fontFamily: THEME.fontMono,
  fontSize: 11.5,
  lineHeight: 1.5,
  overflowWrap: 'anywhere',
  userSelect: 'all',
};

function destinationFrom(locationState: unknown): string {
  if (
    typeof locationState === 'object' &&
    locationState !== null &&
    'from' in locationState &&
    typeof locationState.from === 'string' &&
    locationState.from.startsWith('/') &&
    !locationState.from.startsWith('//') &&
    !locationState.from.startsWith('/login')
  ) {
    return locationState.from;
  }
  return '/model-config';
}

function downloadCredential(credential: string): void {
  const blob = new Blob([
    'CAS Harness customer account credential\n',
    `${credential}\n\n`,
    'Keep this credential private. CAS Harness cannot recover it.\n',
  ], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = 'cas-harness-account-credential.txt';
  anchor.rel = 'noopener noreferrer';
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  globalThis.setTimeout(() => URL.revokeObjectURL(url), 1_000);
}

export default function LoginPage(): JSX.Element {
  const auth = useAccountAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mode, setMode] = useState<LoginMode>('sign-in');
  const [identity, setIdentity] = useState('');
  const [credential, setCredential] = useState(auth.credentialHandoff?.credential ?? '');
  const [inviteCode, setInviteCode] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [generatedCredential, setGeneratedCredential] = useState<string | null>(null);
  const [savedCredential, setSavedCredential] = useState(false);
  const [redeemed, setRedeemed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    if (auth.credentialHandoff?.credential) {
      setCredential(auth.credentialHandoff.credential);
      setMode('sign-in');
    }
  }, [auth.credentialHandoff]);

  const submitLogin = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await auth.login(identity, credential);
      setCredential('');
      navigate(destinationFrom(location.state), { replace: true });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Sign in failed.');
    } finally {
      setBusy(false);
    }
  };

  const prepareInviteCredential = () => {
    setGeneratedCredential(generateAccountCredential());
    setSavedCredential(false);
    setError(null);
    setNotice('Save this credential now. The server will store only its verifier, not the credential.');
  };

  const submitRedemption = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!generatedCredential || !savedCredential) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await auth.redeemInvite({
        code: inviteCode,
        emailOrUsername: identity,
        apiCredential: generatedCredential,
        displayName,
      });
      setRedeemed(true);
      setNotice('Invite redeemed and account session opened. The credential is still shown only so you can finish saving it.');
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Invite redemption failed.');
      setNotice(
        'The same generated credential is retained for a safe retry. Do not generate a different credential after an uncertain response.',
      );
    } finally {
      setBusy(false);
    }
  };

  const copyCredential = async (value: string) => {
    await navigator.clipboard.writeText(value);
    setNotice('Credential copied. Store it in your password manager or secrets vault.');
  };

  return (
    <PageShell showNav={auth.isAuthenticated} cardMaxWidth={560}>
      <GlassPanel intensity="regular" padding={24} ariaLabel="CAS Harness customer account access">
        <h1 style={headingStyle}>Customer account access</h1>
        <p style={textStyle}>
          Use your account identity and private <code>casak_</code> credential. The credential is
          submitted only for authentication and is never saved by this browser application.
        </p>

        {auth.logoutWarning ? (
          <section role="alert" style={{
            marginBottom: 18,
            padding: 12,
            borderRadius: 6,
            border: '1px solid rgba(251,191,36,0.36)',
            background: 'rgba(251,191,36,0.08)',
          }}>
            <p style={{ ...textStyle, margin: 0, color: '#fef3c7' }}>{auth.logoutWarning}</p>
            <button type="button" style={{ ...buttonStyle(), marginTop: 8 }} onClick={auth.clearLogoutWarning}>
              Dismiss warning
            </button>
          </section>
        ) : null}

        {auth.credentialHandoff ? (
          <section aria-label="Rotated account credential" style={{ marginBottom: 18 }}>
            <p role="alert" style={{ ...textStyle, color: '#fef3c7' }}>
              Credential rotation succeeded and revoked the old session. Save this new credential,
              then sign in again. It will disappear on reload.
            </p>
            <code style={credentialStyle}>{auth.credentialHandoff.credential}</code>
            <div style={{ display: 'flex', gap: 8, marginTop: 8, flexWrap: 'wrap' }}>
              <button type="button" style={buttonStyle()} onClick={() => void copyCredential(auth.credentialHandoff!.credential)}>
                Copy credential
              </button>
              <button type="button" style={buttonStyle()} onClick={() => downloadCredential(auth.credentialHandoff!.credential)}>
                Download credential
              </button>
            </div>
          </section>
        ) : null}

        <div role="tablist" aria-label="Account access method" style={{ display: 'flex', gap: 8, marginBottom: 18 }}>
          <button
            type="button"
            role="tab"
            aria-selected={mode === 'sign-in'}
            style={buttonStyle(mode === 'sign-in')}
            onClick={() => { setMode('sign-in'); setError(null); }}
          >
            Sign in
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mode === 'redeem'}
            style={buttonStyle(mode === 'redeem')}
            onClick={() => { setMode('redeem'); setError(null); }}
          >
            Redeem invite
          </button>
        </div>

        {mode === 'sign-in' ? (
          <form onSubmit={(event) => void submitLogin(event)}>
            <div style={fieldStyle}>
              <label htmlFor="account-identity" style={labelStyle}>Email or username</label>
              <input
                id="account-identity"
                value={identity}
                onChange={(event) => setIdentity(event.target.value)}
                autoComplete="username"
                required
                style={inputStyle}
              />
            </div>
            <div style={fieldStyle}>
              <label htmlFor="account-credential" style={labelStyle}>Account credential</label>
              <input
                id="account-credential"
                type="password"
                value={credential}
                onChange={(event) => setCredential(event.target.value)}
                autoComplete="off"
                spellCheck={false}
                pattern="casak_[A-Za-z0-9_-]{43,128}"
                required
                style={{ ...inputStyle, fontFamily: THEME.fontMono }}
              />
            </div>
            <button type="submit" disabled={busy} style={buttonStyle(true, busy)}>
              {busy ? 'Signing in...' : 'Sign in securely'}
            </button>
          </form>
        ) : (
          <form onSubmit={(event) => void submitRedemption(event)}>
            <div style={fieldStyle}>
              <label htmlFor="invite-code" style={labelStyle}>Invite code</label>
              <input id="invite-code" value={inviteCode} onChange={(event) => setInviteCode(event.target.value)} autoComplete="one-time-code" required style={inputStyle} />
            </div>
            <div style={fieldStyle}>
              <label htmlFor="invite-identity" style={labelStyle}>Email or username</label>
              <input id="invite-identity" value={identity} onChange={(event) => setIdentity(event.target.value)} autoComplete="username" required style={inputStyle} />
            </div>
            <div style={fieldStyle}>
              <label htmlFor="invite-display-name" style={labelStyle}>Display name (optional)</label>
              <input id="invite-display-name" value={displayName} onChange={(event) => setDisplayName(event.target.value)} autoComplete="name" style={inputStyle} />
            </div>

            {!generatedCredential ? (
              <button type="button" style={buttonStyle(true)} onClick={prepareInviteCredential}>
                Generate my account credential
              </button>
            ) : (
              <section aria-label="Generated account credential">
                <p style={{ ...textStyle, color: '#fef3c7' }}>
                  This is the only copy. CAS Harness cannot recover it. A failed or interrupted
                  redemption retry must reuse this exact value.
                </p>
                <code style={credentialStyle}>{generatedCredential}</code>
                <div style={{ display: 'flex', gap: 8, marginTop: 8, flexWrap: 'wrap' }}>
                  <button type="button" style={buttonStyle()} onClick={() => void copyCredential(generatedCredential)}>Copy credential</button>
                  <button type="button" style={buttonStyle()} onClick={() => downloadCredential(generatedCredential)}>Download credential</button>
                </div>
                <label style={{ ...textStyle, display: 'flex', gap: 8, alignItems: 'flex-start' }}>
                  <input type="checkbox" checked={savedCredential} onChange={(event) => setSavedCredential(event.target.checked)} />
                  I saved this credential in a secure place.
                </label>
                {!redeemed ? (
                  <button type="submit" disabled={busy || !savedCredential} style={buttonStyle(true, busy || !savedCredential)}>
                    {busy ? 'Redeeming invite...' : 'Redeem invite and sign in'}
                  </button>
                ) : (
                  <button type="button" style={buttonStyle(true)} onClick={() => navigate(destinationFrom(location.state), { replace: true })}>
                    Continue to model selection
                  </button>
                )}
              </section>
            )}
          </form>
        )}

        {error ? <p role="alert" style={{ ...textStyle, color: '#fecaca' }}>{error}</p> : null}
        {notice ? <p role="status" style={textStyle}>{notice}</p> : null}
        <p style={{ ...textStyle, marginTop: 20, paddingTop: 14, borderTop: '1px solid rgba(255,255,255,0.06)' }}>
          First-owner bootstrap, owner recovery, and platform tenant provisioning are operator-only
          deployment workflows. Their secrets are never accepted or exposed by this customer UI.
        </p>
      </GlassPanel>
    </PageShell>
  );
}
