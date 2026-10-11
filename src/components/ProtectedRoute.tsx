import { Navigate, useLocation } from "react-router-dom";
import { isAuthenticated } from "../lib/auth";

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const location = useLocation();

  if (!isAuthenticated()) {
    // Preserve path + query (e.g. /research?ticker=MSFT) so the pending
    // research resumes after auth. Research intent opens the Sign Up tab.
    return (
      <Navigate
        to="/auth"
        state={{
          from: location.pathname + location.search,
          ...(location.pathname.startsWith("/research") && { mode: "signup" }),
        }}
        replace
      />
    );
  }

  return <>{children}</>;
}
