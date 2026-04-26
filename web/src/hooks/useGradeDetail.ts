import { useEffect, useState } from "react";
import { fetchTransferGrade } from "@/lib/api";
import type { GradeDetail } from "@/types/grade";

/**
 * Module-level cache keyed by transfer_id.
 *
 * Shared across every consumer of this hook so that hovering the badge (the
 * tooltip flow) and then expanding the row (the breakdown panel flow) for
 * the same transfer reuses the already-fetched detail without a second round
 * trip. Entries can be `null` for transfers that came back 204 (ungradeable
 * — never re-fetch those either).
 */
const cache = new Map<number, GradeDetail | null>();

interface UseGradeDetailResult {
  detail: GradeDetail | null;
  loading: boolean;
}

/**
 * Lazy-load the per-component grade breakdown for a transfer.
 *
 * Pass `enabled = false` to defer the fetch (e.g. while the badge is idle and
 * the user hasn't hovered yet). When the flag flips true the hook fires the
 * request unless the detail is already cached.
 */
export function useGradeDetail(transferId: number, enabled = true): UseGradeDetailResult {
  const cached = cache.get(transferId) ?? null;
  const cacheHit = cache.has(transferId);

  const [detail, setDetail] = useState<GradeDetail | null>(cached);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!enabled || cache.has(transferId)) {
      // If a different transfer was previously displayed, refresh from cache.
      if (cache.has(transferId)) setDetail(cache.get(transferId) ?? null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    fetchTransferGrade(transferId)
      .then((d) => {
        cache.set(transferId, d);
        if (!cancelled) setDetail(d);
      })
      .catch(() => {
        // Surface nothing — the consumer falls back to the abbreviated grade.
        if (!cancelled) setDetail(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [transferId, enabled]);

  return { detail, loading: loading && !cacheHit };
}
