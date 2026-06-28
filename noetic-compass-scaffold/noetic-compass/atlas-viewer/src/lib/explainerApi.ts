const TOKEN_STORAGE_KEY = 'atlasViewerAuthToken';

export interface ExplainerChatResponse {
  answer: string;
  sources: string[];
  used_gemini: boolean;
  model: string;
  safety_mode: string;
}

async function ensureAuthToken(): Promise<string> {
  const existing = window.sessionStorage.getItem(TOKEN_STORAGE_KEY);
  if (existing) return existing;

  const response = await fetch('/api/auth/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: 'atlas-explainer-user' }),
  });
  if (!response.ok) {
    throw new Error(`Unable to mint explainer session (${response.status})`);
  }
  const payload = (await response.json()) as { token?: string };
  if (!payload.token) {
    throw new Error('Explainer session response did not include a token.');
  }
  window.sessionStorage.setItem(TOKEN_STORAGE_KEY, payload.token);
  return payload.token;
}

export async function askExplainer(question: string): Promise<ExplainerChatResponse> {
  const token = await ensureAuthToken();
  const response = await fetch('/api/explainer/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ question }),
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Explainer request failed (${response.status})`);
  }
  return (await response.json()) as ExplainerChatResponse;
}
