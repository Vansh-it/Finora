import { Component, type ReactNode } from "react";
import { Link } from "react-router-dom";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("ErrorBoundary caught:", error, info);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;

      return (
        <div className="mx-auto flex min-h-[50vh] max-w-2xl flex-col items-center justify-center px-4 py-20 text-center">
          <div className="border-2 border-ink/20 bg-paper p-10">
            <h2 className="font-serif text-3xl font-semibold text-ink">
              Something went wrong.
            </h2>
            <p className="mt-3 max-w-md text-sm leading-relaxed text-ink-2">
              {this.state.error?.message?.includes("Failed to fetch") || this.state.error?.message?.includes("Could not reach")
                ? "Could not connect to the Finora backend. Make sure the server is running."
                : "An unexpected error occurred. Please try refreshing the page."}
            </p>
            <div className="mt-8 flex justify-center gap-4">
              <button
                onClick={() => {
                  this.setState({ hasError: false, error: null });
                  window.location.reload();
                }}
                className="border-2 border-ink bg-paper px-6 py-3 font-mono text-xs font-bold tracking-wider text-ink uppercase transition-colors hover:bg-ink hover:text-paper"
              >
                Reload Page
              </button>
              <Link
                to="/"
                className="border-2 border-ink bg-ink px-6 py-3 font-mono text-xs font-bold tracking-wider text-paper uppercase transition-colors hover:bg-ink-2"
              >
                Go Home
              </Link>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
