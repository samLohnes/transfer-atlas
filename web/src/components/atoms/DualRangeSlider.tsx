import { useCallback, useRef } from "react";

interface DualRangeSliderProps {
  min: number;
  max: number;
  valueLow: number;
  valueHigh: number;
  onChange: (low: number, high: number) => void;
  className?: string;
}

/** A single-track slider with two draggable thumbs for min/max selection. */
export function DualRangeSlider({
  min,
  max,
  valueLow,
  valueHigh,
  onChange,
  className = "",
}: DualRangeSliderProps) {
  const trackRef = useRef<HTMLDivElement>(null);

  const range = max - min || 1;
  const lowPct = ((valueLow - min) / range) * 100;
  const highPct = ((valueHigh - min) / range) * 100;

  const getValueFromEvent = useCallback(
    (clientX: number): number => {
      if (!trackRef.current) return min;
      const rect = trackRef.current.getBoundingClientRect();
      const pct = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
      return Math.round(min + pct * range);
    },
    [min, range],
  );

  const startDrag = useCallback(
    (thumb: "low" | "high") => (e: React.PointerEvent) => {
      e.preventDefault();
      const target = e.currentTarget as HTMLElement;
      target.setPointerCapture(e.pointerId);

      const onMove = (ev: PointerEvent) => {
        const val = getValueFromEvent(ev.clientX);
        if (thumb === "low") {
          onChange(Math.min(val, valueHigh), valueHigh);
        } else {
          onChange(valueLow, Math.max(val, valueLow));
        }
      };

      const onUp = () => {
        target.removeEventListener("pointermove", onMove);
        target.removeEventListener("pointerup", onUp);
      };

      target.addEventListener("pointermove", onMove);
      target.addEventListener("pointerup", onUp);
    },
    [getValueFromEvent, onChange, valueLow, valueHigh],
  );

  return (
    <div ref={trackRef} className={`relative h-5 flex items-center ${className}`}>
      {/* Track background */}
      <div className="absolute inset-x-0 h-[3px] rounded-full bg-gradient-to-r from-[#1a2e22] to-[#2d4a38]" />

      {/* Active range highlight */}
      <div
        className="absolute h-[3px] rounded-full bg-[#4ade80]/40"
        style={{ left: `${lowPct}%`, width: `${highPct - lowPct}%` }}
      />

      {/* Low thumb */}
      <div
        className="absolute w-[14px] h-[14px] rounded-full bg-[#4ade80] border-2 border-[#0a1410] shadow-[0_0_8px_rgba(74,222,128,0.4)] cursor-grab active:cursor-grabbing hover:shadow-[0_0_14px_rgba(74,222,128,0.6)] hover:scale-110 transition-shadow"
        style={{ left: `${lowPct}%`, transform: "translateX(-50%)" }}
        onPointerDown={startDrag("low")}
      />

      {/* High thumb */}
      <div
        className="absolute w-[14px] h-[14px] rounded-full bg-[#4ade80] border-2 border-[#0a1410] shadow-[0_0_8px_rgba(74,222,128,0.4)] cursor-grab active:cursor-grabbing hover:shadow-[0_0_14px_rgba(74,222,128,0.6)] hover:scale-110 transition-shadow"
        style={{ left: `${highPct}%`, transform: "translateX(-50%)" }}
        onPointerDown={startDrag("high")}
      />
    </div>
  );
}
