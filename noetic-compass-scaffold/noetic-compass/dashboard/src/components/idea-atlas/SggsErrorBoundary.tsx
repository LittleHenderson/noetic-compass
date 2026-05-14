/**
 * SggsErrorBoundary — catches errors thrown anywhere inside SggsScene
 * (WebGL renderer creation failure, unsupported browser, lazy chunk
 * load failure after the request starts, runtime errors in the
 * animation loop) and renders a friendly fallback instead of letting
 * the whole IdeaAtlasPage crash.
 *
 * Per Codex audit 8939e62 blocker 2 (2026-05-13): "Suspense handles
 * the lazy chunk loading wait, but it does not catch WebGLRenderer
 * creation failure, unsupported WebGL, chunk load error after request
 * starts, or runtime errors inside SggsScene." A clean fallback is
 * required for a stakeholder-facing demo tab.
 *
 * Kept as a class component because React error boundaries are only
 * available as class components in React 19.
 */
import { Component, type ErrorInfo, type ReactNode } from 'react';

interface SggsErrorBoundaryProps {
  children: ReactNode;
  /** Optional callback for telemetry hooks; logged to console by
   *  default. */
  onError?: (error: Error, info: ErrorInfo) => void;
}

interface SggsErrorBoundaryState {
  error: Error | null;
}

export class SggsErrorBoundary extends Component<
  SggsErrorBoundaryProps,
  SggsErrorBoundaryState
> {
  state: SggsErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): SggsErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    if (this.props.onError) {
      this.props.onError(error, info);
    } else if (typeof console !== 'undefined') {
      // eslint-disable-next-line no-console
      console.error('[SGGS] 3D scene crashed:', error, info);
    }
  }

  reset = (): void => {
    this.setState({ error: null });
  };

  render(): ReactNode {
    if (this.state.error !== null) {
      return (
        <div
          role="alert"
          data-testid="sggs-error-fallback"
          className="flex h-full min-h-[560px] w-full items-center justify-center rounded-lg border border-rose-500/30 bg-rose-500/5 p-6 text-center"
        >
          <div className="flex max-w-md flex-col gap-3 font-mono text-xs text-rose-200">
            <div className="text-sm font-semibold text-rose-300">
              3D scene could not start
            </div>
            <p className="text-slate-300">
              Try refreshing, updating your browser, or using the TRACE
              view (2D SVG) instead — it renders the same trace without
              WebGL.
            </p>
            <details className="text-[10px] text-slate-500">
              <summary className="cursor-pointer">technical detail</summary>
              <pre className="mt-2 whitespace-pre-wrap text-left text-slate-500">
                {this.state.error.message || String(this.state.error)}
              </pre>
            </details>
            <button
              type="button"
              onClick={this.reset}
              className="self-center rounded border border-rose-400/40 px-3 py-1 text-rose-200 transition-colors hover:bg-rose-500/10"
            >
              Try again
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

export default SggsErrorBoundary;
