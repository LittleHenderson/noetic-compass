/* ── CAS Forex — Error Boundary ──
 * Stops a single page's render error from blanking the WHOLE app (which also
 * took the floating assistant down with it). Catches the throw, shows a readable
 * panel with the error, and keeps the rest of the shell — including the floating
 * assistant — alive. Resets when the active page changes.
 */

import { Component, type ErrorInfo, type ReactNode } from "react";

interface ErrorBoundaryProps {
  children: ReactNode;
  /** When this changes (e.g. the active page), the boundary resets and retries. */
  resetKey?: string | number;
  label?: string;
}

interface ErrorBoundaryState {
  error: Error | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidUpdate(prev: ErrorBoundaryProps) {
    // A new page mounted — clear the error so the new page gets a clean render.
    if (prev.resetKey !== this.props.resetKey && this.state.error) {
      this.setState({ error: null });
    }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // Surface it for debugging without taking the app down.
    // eslint-disable-next-line no-console
    console.error(`[CAS Forex] ${this.props.label ?? "page"} render error:`, error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="error-boundary-panel" role="alert">
          <div className="error-boundary-title">This screen hit an error and was contained</div>
          <div className="error-boundary-detail">
            The rest of the app (and the assistant) are still working. You can switch pages and come back.
          </div>
          <pre className="error-boundary-message">{String(this.state.error?.message ?? this.state.error)}</pre>
        </div>
      );
    }
    return this.props.children;
  }
}
