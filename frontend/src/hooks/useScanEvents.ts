import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { tokenStorage } from "@/lib/auth";
import { api } from "@/lib/api";

type ScanStatus = "pending" | "running" | "completed" | "failed";

export function useScanEvents(scanId: number | null) {
  const [status, setStatus] = useState<ScanStatus | null>(null);
  const qc = useQueryClient();

  useEffect(() => {
    setStatus(null);
    if (scanId === null) return;

    const token = tokenStorage.getAccess();
    if (!token) return;

    const finalize = (s: ScanStatus) => {
      setStatus(s);
      if (s === "completed" || s === "failed") {
        void qc.invalidateQueries({ queryKey: ["scans"] });
      }
    };

    // EventSource doesn't support custom headers — pass token as query param
    const url = `/api/v1/scans/${scanId}/events?token=${encodeURIComponent(token)}`;
    const es = new EventSource(url);

    es.addEventListener("status", (e: MessageEvent) => {
      const data = JSON.parse(e.data) as { id: number; status: ScanStatus };
      setStatus(data.status);

      if (data.status === "completed" || data.status === "failed") {
        void qc.invalidateQueries({ queryKey: ["scans"] });
        es.close();
      }
    });

    es.onerror = () => {
      es.close();
      // Fallback: if the stream drops before the final event arrives, fetch
      // the current status via REST so the form doesn't stay permanently locked.
      api
        .get<{ id: number; status: ScanStatus }>(`/api/v1/scans/${scanId}/status`)
        .then((data) => finalize(data.status))
        .catch(() => {/* ignore — the scan list will refresh on next invalidation */});
    };

    return () => {
      es.close();
    };
  }, [scanId, qc]);

  return status;
}
