import { Navigate, Route, Routes } from "react-router-dom";

import { ProtectedRoute } from "@/components/ProtectedRoute";
import { DashboardPage } from "@/pages/DashboardPage";
import { DiffPage } from "@/pages/DiffPage";
import { DomainsPage } from "@/pages/DomainsPage";
import { LoginPage } from "@/pages/LoginPage";
import { RegisterPage } from "@/pages/RegisterPage";
import { ScanDetailPage } from "@/pages/ScanDetailPage";
import { ApiKeysPage } from "@/pages/ApiKeysPage";
import { AuditPage } from "@/pages/AuditPage";
import { ScheduledScansPage } from "@/pages/ScheduledScansPage";
import { SecurityPage } from "@/pages/SecurityPage";
import { WebhooksPage } from "@/pages/WebhooksPage";

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/domains"
        element={
          <ProtectedRoute>
            <DomainsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/scheduled"
        element={
          <ProtectedRoute>
            <ScheduledScansPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/webhooks"
        element={
          <ProtectedRoute>
            <WebhooksPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/security"
        element={
          <ProtectedRoute>
            <SecurityPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/api-keys"
        element={
          <ProtectedRoute>
            <ApiKeysPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/audit"
        element={
          <ProtectedRoute>
            <AuditPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/scans/:id"
        element={
          <ProtectedRoute>
            <ScanDetailPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/diff"
        element={
          <ProtectedRoute>
            <DiffPage />
          </ProtectedRoute>
        }
      />
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

export default App;
