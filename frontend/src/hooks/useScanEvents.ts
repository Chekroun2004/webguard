import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { tokenStorage } from "@/lib/auth";

type ScanStatus = "pending" | "running" | "completed" | "failed";

/**
 * Subscribes to the SSE stream for a given scan.
 * Automatically invalidates the scan query when status reaches completed/failed.
 */
export function useScanEvents(scanId: number | null) {
  const [status, setStatus] = useState<ScanStatus | null>(null);
  const qc = useQueryClient();

  useEffect(() => {
    if (scanId === null) return;

    const token = tokenStorage.getAccess();
    if (!token) return;

    // EventSource doesn't support custom headers — pass token as query param
    const url = `/api/v1/scans/${scanId}/events?token=${encodeURIComponent(token)}`;
    const es = new EventSource(url);

    es.addEventListener("status", (e: MessageEvent) => {
      const data = JSON.parse(e.data) as { id: number; status: ScanStatus };
      setStatus(data.status);

      if (data.status === "completed" || data.status === "failed") {
        // Refresh scan detail + list in the cache
        void qc.invalidateQueries({ queryKey: ["scans"] });
        es.close();
      }
    });

    es.onerror = () => {
      es.close();
    };

    return () => {
      es.close();
    };
  }, [scanId, qc]);

  return status;
}
