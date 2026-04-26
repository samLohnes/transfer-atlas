import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { GradeBadge } from "@/components/atoms/GradeBadge";
import { GradeTooltip } from "@/components/molecules/GradeTooltip";
import { fetchTransferGrade } from "@/lib/api";
import type { GradeDetail } from "@/types/grade";

interface GradeBadgeWithTooltipProps {
  transferId: number;
  letterGrade: string;
  compositeScore: number;
  isComplete: boolean;
  worthTheFee: boolean;
  playerId?: number | null;
  size?: "sm" | "md";
}

/** Delay before hiding the tooltip on mouse-leave so users can move into it. */
const HIDE_DELAY_MS = 150;

/** Tooltip vertical gap above the badge (in px). */
const TOOLTIP_GAP_PX = 8;
/** Approximate tooltip height (used for above/below flip decision). */
const TOOLTIP_ESTIMATED_HEIGHT_PX = 220;

/**
 * Renders the grade badge and lazy-loads the full breakdown into a hover
 * tooltip. The compact grade comes from the parent (already in the transfer
 * list response); only the per-component breakdown is fetched on demand.
 */
export function GradeBadgeWithTooltip({
  transferId,
  letterGrade,
  compositeScore,
  isComplete,
  worthTheFee: _worthTheFee,
  playerId,
  size = "md",
}: GradeBadgeWithTooltipProps) {
  const navigate = useNavigate();
  const anchorRef = useRef<HTMLSpanElement | null>(null);
  const hideTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const cachedDetailRef = useRef<GradeDetail | null>(null);

  const [tooltipOpen, setTooltipOpen] = useState(false);
  const [tooltipPos, setTooltipPos] = useState<{ top: number; left: number } | null>(null);
  const [detail, setDetail] = useState<GradeDetail | null>(null);
  const [loading, setLoading] = useState(false);

  const clearHideTimer = useCallback(() => {
    if (hideTimeoutRef.current) {
      clearTimeout(hideTimeoutRef.current);
      hideTimeoutRef.current = null;
    }
  }, []);

  const computeTooltipPosition = useCallback((anchor: HTMLSpanElement) => {
    const rect = anchor.getBoundingClientRect();
    const placeAbove = rect.top > TOOLTIP_ESTIMATED_HEIGHT_PX + TOOLTIP_GAP_PX;
    const top = placeAbove
      ? rect.top - TOOLTIP_GAP_PX - TOOLTIP_ESTIMATED_HEIGHT_PX
      : rect.bottom + TOOLTIP_GAP_PX;
    const left = Math.max(8, Math.min(window.innerWidth - 388, rect.left));
    return { top, left };
  }, []);

  const handleEnter = useCallback(() => {
    clearHideTimer();
    if (anchorRef.current) {
      setTooltipPos(computeTooltipPosition(anchorRef.current));
    }
    setTooltipOpen(true);

    if (cachedDetailRef.current) {
      setDetail(cachedDetailRef.current);
      return;
    }
    setLoading(true);
    fetchTransferGrade(transferId)
      .then((d) => {
        cachedDetailRef.current = d;
        setDetail(d);
      })
      .catch(() => {
        // Network failure leaves `detail` null; the tooltip degrades to
        // showing the abbreviated header only. We intentionally don't surface
        // the error to the user — a hover tooltip isn't worth a toast.
      })
      .finally(() => setLoading(false));
  }, [transferId, clearHideTimer, computeTooltipPosition]);

  const handleLeave = useCallback(() => {
    clearHideTimer();
    hideTimeoutRef.current = setTimeout(() => setTooltipOpen(false), HIDE_DELAY_MS);
  }, [clearHideTimer]);

  // Cleanup the hide timer on unmount so we don't try to setState on a dead component.
  useEffect(() => () => clearHideTimer(), [clearHideTimer]);

  const handleClick = useCallback(() => {
    if (playerId != null) navigate(`/players/${playerId}`);
  }, [navigate, playerId]);

  return (
    <span
      ref={anchorRef}
      className="inline-flex"
      onMouseEnter={handleEnter}
      onMouseLeave={handleLeave}
      onFocus={handleEnter}
      onBlur={handleLeave}
    >
      <GradeBadge
        letterGrade={letterGrade}
        compositeScore={compositeScore}
        isComplete={isComplete}
        size={size}
        onClick={playerId != null ? handleClick : undefined}
      />
      {tooltipOpen && tooltipPos && (
        <GradeTooltip
          position={tooltipPos}
          compositeScore={detail?.composite_score ?? compositeScore}
          letterGrade={detail?.letter_grade ?? letterGrade}
          isComplete={detail?.is_complete ?? isComplete}
          components={detail?.components ?? {}}
          modelVersion={detail?.model_version ?? null}
          loading={loading}
          onMouseEnter={clearHideTimer}
          onMouseLeave={handleLeave}
        />
      )}
    </span>
  );
}
