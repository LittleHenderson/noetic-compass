import { ApiError } from '../../api/client';

const STATUS_LABELS: Record<number, string> = {
  401: 'Unauthorized — check your JWT token',
  403: 'Forbidden',
  404: 'Not found',
  422: 'Validation error',
  429: 'Rate limited — try again later',
  500: 'Server error',
  502: 'LLM provider error',
};

export function ErrorBanner({ error }: { error: Error | null }) {
  if (!error) return null;

  let message = error.message;
  if (error instanceof ApiError) {
    const label = STATUS_LABELS[error.status];
    message = label ? `${label}: ${error.detail}` : `Error ${error.status}: ${error.detail}`;
  }

  return (
    <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
      {message}
    </div>
  );
}
