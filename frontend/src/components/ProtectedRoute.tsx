import { Navigate } from "react-router-dom";

import { useCurrentUser } from "@/hooks/useAuth";
import { tokenStorage } from "@/lib/auth";

type Props = { children: React.ReactNode };

export function ProtectedRoute({ children }: Props) {
  const { data: user, isLoading } = useCurrentUser();

  // No token at all → redirect immediately (no network call needed)
  if (!tokenStorage.getAccess()) {
    return <Navigate to="/login" replace />;
  }

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-muted-foreground">
        Chargement…
      </div>
    );
  }

  // Token present but invalid / expired
  if (!user) {
    tokenStorage.clear();
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}
