import { useMemo, useRef, useState } from "react";
import { Map as MapGL } from "react-map-gl/maplibre";
import "maplibre-gl/dist/maplibre-gl.css";
import { ArcLayer, ScatterplotLayer } from "deck.gl";
import { DeckGL } from "deck.gl";
import { MapTooltip } from "./MapTooltip";
import type { TooltipData } from "./MapTooltip";
import { Spinner } from "@/components/atoms/Spinner";
import type { Country, CountryFlow, CountrySummary } from "@/types/country";

interface MapViewProps {
  countries: Country[];
  flows: CountryFlow[];
  countrySummaries: CountrySummary[];
  isLoading: boolean;
  selectedCountryId: number | null;
  onSelectCountry: (id: number | null) => void;
}

const INITIAL_VIEW_STATE = {
  latitude: 48,
  longitude: 10,
  zoom: 3,
  pitch: 0,
  bearing: 0,
};

const MAP_STYLE = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";

/** Interactive geographic map with country nodes and flow arcs. */
export function MapView({
  countries,
  flows,
  countrySummaries,
  isLoading,
  selectedCountryId,
  onSelectCountry,
}: MapViewProps) {
  const [tooltip, setTooltip] = useState<TooltipData | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Build lookup maps
  const countryById = useMemo(() => {
    const m = new Map<number, Country>();
    countries.forEach((c) => m.set(c.id, c));
    return m;
  }, [countries]);

  const summaryById = useMemo(() => {
    const m = new Map<number, CountrySummary>();
    countrySummaries.forEach((s) => m.set(s.country_id, s));
    return m;
  }, [countrySummaries]);

  // Compute scales
  const maxAbsNetSpend = useMemo(() => {
    if (countrySummaries.length === 0) return 1;
    return Math.max(...countrySummaries.map((s) => Math.abs(s.net_spend_eur)), 1);
  }, [countrySummaries]);

  const maxFlowFee = useMemo(() => {
    if (flows.length === 0) return 1;
    return Math.max(...flows.map((f) => f.total_fee_eur), 1);
  }, [flows]);

  const flowThreshold = maxFlowFee * 0.005;

  // Total transfers per country for tooltip and node sizing
  const countryTransferTotals = useMemo(() => {
    const totals = new Map<number, { volume: number; count: number }>();
    flows.forEach((f) => {
      const from = totals.get(f.from_country_id) ?? { volume: 0, count: 0 };
      from.volume += f.total_fee_eur;
      from.count += f.transfer_count;
      totals.set(f.from_country_id, from);

      const to = totals.get(f.to_country_id) ?? { volume: 0, count: 0 };
      to.volume += f.total_fee_eur;
      to.count += f.transfer_count;
      totals.set(f.to_country_id, to);
    });
    return totals;
  }, [flows]);

  const maxVolume = useMemo(() => {
    if (countryTransferTotals.size === 0) return 1;
    return Math.max(...Array.from(countryTransferTotals.values()).map((t) => t.volume), 1);
  }, [countryTransferTotals]);

  // Country node color
  function getNodeColor(countryId: number): [number, number, number, number] {
    const summary = summaryById.get(countryId);
    if (!summary || summary.net_spend_eur === 0) return [107, 114, 128, 128]; // gray

    const ratio = Math.abs(summary.net_spend_eur) / maxAbsNetSpend;
    const alpha = Math.round((0.3 + 0.7 * ratio) * 255);

    if (summary.net_spend_eur > 0) return [239, 68, 68, alpha]; // red (spender)
    return [34, 197, 94, alpha]; // green (receiver)
  }

  // Layers
  const layers = useMemo(() => {
    const scatterLayer = new ScatterplotLayer({
      id: "country-nodes",
      data: countries,
      getPosition: (d: Country) => [d.longitude, d.latitude],
      getRadius: (d: Country) => {
        const vol = countryTransferTotals.get(d.id)?.volume ?? 0;
        const normalized = Math.sqrt(vol / maxVolume);
        return 30000 + normalized * 120000;
      },
      getFillColor: (d: Country) => getNodeColor(d.id),
      getLineColor: [255, 255, 255, 80],
      lineWidthMinPixels: 1,
      stroked: true,
      pickable: true,
      radiusMinPixels: 5,
      radiusMaxPixels: 30,
      onClick: (info: { object?: Country }) => {
        if (info.object) onSelectCountry(info.object.id);
      },
      onHover: (info: { object?: Country; x: number; y: number }) => {
        if (info.object) {
          const summary = summaryById.get(info.object.id);
          const totals = countryTransferTotals.get(info.object.id);
          setTooltip({
            type: "country",
            x: info.x,
            y: info.y,
            countryName: info.object.name,
            netSpend: summary?.net_spend_eur ?? 0,
            totalTransfers: totals?.count ?? 0,
          });
        } else {
          setTooltip(null);
        }
      },
      updateTriggers: {
        getFillColor: [countrySummaries],
        getRadius: [countryTransferTotals],
      },
    });

    const filteredFlows = flows.filter((f) => f.total_fee_eur >= flowThreshold);

    const arcData = filteredFlows
      .map((f) => {
        const from = countryById.get(f.from_country_id);
        const to = countryById.get(f.to_country_id);
        if (!from || !to) return null;
        return { ...f, fromPos: [from.longitude, from.latitude], toPos: [to.longitude, to.latitude] };
      })
      .filter(Boolean);

    const maxLogFee = Math.log10(Math.max(maxFlowFee, 1));

    const arcLayer = new ArcLayer({
      id: "flow-arcs",
      data: arcData,
      getSourcePosition: (d: (typeof arcData)[0]) => d!.fromPos as [number, number],
      getTargetPosition: (d: (typeof arcData)[0]) => d!.toPos as [number, number],
      getSourceColor: [74, 222, 128, 178],
      getTargetColor: [74, 222, 128, 178],
      getWidth: (d: (typeof arcData)[0]) => {
        const logFee = Math.log10(Math.max(d!.total_fee_eur, 1));
        const normalized = logFee / maxLogFee;
        return 1 + normalized * 11;
      },
      getHeight: 0.5,
      pickable: true,
      onHover: (info: { object?: (typeof arcData)[0]; x: number; y: number }) => {
        if (info.object) {
          setTooltip({
            type: "arc",
            x: info.x,
            y: info.y,
            fromCountry: info.object.from_country_name,
            toCountry: info.object.to_country_name,
            fee: info.object.total_fee_eur,
            transferCount: info.object.transfer_count,
          });
        } else {
          setTooltip(null);
        }
      },
      updateTriggers: {
        getWidth: [maxFlowFee],
      },
    });

    return [arcLayer, scatterLayer];
  }, [countries, flows, countrySummaries, countryTransferTotals, maxVolume, maxAbsNetSpend, maxFlowFee, flowThreshold, countryById, summaryById, onSelectCountry]);

  return (
    <div ref={containerRef} className="relative w-full h-full">
      <DeckGL
        initialViewState={INITIAL_VIEW_STATE}
        controller
        layers={layers}
        onClick={(info: { layer?: unknown }) => {
          if (!info.layer) onSelectCountry(null);
        }}
        style={{ position: "absolute", inset: 0 }}
      >
        <MapGL mapStyle={MAP_STYLE} />
      </DeckGL>

      <MapTooltip data={tooltip} />

      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/20 pointer-events-none">
          <Spinner size="lg" />
        </div>
      )}
    </div>
  );
}
