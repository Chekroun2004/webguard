import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { tokenStorage } from "@/lib/auth";
import { api } from "@/lib/api";

type ScanStatus = "pending" | "running" | "completed" | "failed";

const TERMINAL: ReadonlySet<ScanStatus> = new Set(["completed", "failed"]);

export function useScanEvents(scanId: number | null) {
  const [status, setStatus] = useState<ScanStatus | null>(null);
  const qc = useQueryClient();

  useEffect(() => {
    setStatus(null);
    if (scanId === null) return;

    const token = tokenStorage.getAccess();
    if (!token) return;

    let cancelled = false;

    const finalize = (s: ScanStatus) => {
      if (cancelled) return;
      setStatus(s);
      if (TERMINAL.has(s)) {
        void qc.invalidateQueries({ queryKey: ["scans"] });
      }
    };

    // Poll the REST status endpoint with exponential backoff until the scan
    // reaches a terminal state. Used as fallback when the SSE stream drops.
    const pollUntilDone = (delay = 1000) => {
      if (cancelled) return;
      setTimeout(async () => {
        if (cancelled) return;
        try {
          const data = await api.get<{ id: number; status: ScanStatus }>(
            `/api/v1/scans/${scanId}/status`
          );
          finalize(data.status);
          if (!TERMINAL.has(data.status)) {
            pollUntilDone(Math.min(delay * 2, 8000));
          }
        } catch {
          pollUntilDone(delay);
        }
      }, delay);
    };

    // EventSource doesn't support custom headers — pass token as query param
    const url = `/api/v1/scans/${scanId}/events?token=${encodeURIComponent(token)}`;
    const es = new EventSource(url);

    es.addEventListener("status", (e: MessageEvent) => {
      const data = JSON.parse(e.data) as { id: number; status: ScanStatus };
      if (!cancelled) setStatus(data.status);

      if (TERMINAL.has(data.status)) {
        void qc.invalidateQueries({ queryKey: ["scans"] });
        es.close();
      }
    });

    es.onerror = () => {
      es.close();
      // SSE dropped — fall back to REST polling until terminal state so the
      // form is never permanently locked by a non-terminal stale status.
      pollUntilDone();
    };

    return () => {
      cancelled = true;
      es.close();
    };
  }, [scanId, qc]);

  return status;
}
