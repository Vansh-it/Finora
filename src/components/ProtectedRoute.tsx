import { Navigate, useLocation } from "react-router-dom";
import { isAuthenticated } from "../lib/auth";

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const location = useLocation();

  if (!isAuthenticated()) {
    return <Navigate to="/auth" state={{ from: location.pathname }} replace />;
  }

  return <>{children}</>;
}
