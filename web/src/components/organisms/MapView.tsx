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

    // Collapse flows into net flows per country pair
    const netFlowMap = new Map<string, {
      countryA_id: number; countryA_name: string;
      countryB_id: number; countryB_name: string;
      netFee: number; totalTransfers: number;
    }>();
    for (const f of flows) {
      const key = [Math.min(f.from_country_id, f.to_country_id), Math.max(f.from_country_id, f.to_country_id)].join("-");
      const existing = netFlowMap.get(key);
      if (existing) {
        // from→to means to_country is paying (buying). Net = buyer spend.
        // If from < to matches countryA < countryB, A→B direction is positive
        if (f.from_country_id === existing.countryA_id) {
          existing.netFee -= f.total_fee_eur; // A sold to B, B spent → B's direction
        } else {
          existing.netFee += f.total_fee_eur; // B sold to A, A spent → A's direction
        }
        existing.totalTransfers += f.transfer_count;
      } else {
        const aId = Math.min(f.from_country_id, f.to_country_id);
        const bId = Math.max(f.from_country_id, f.to_country_id);
        const aName = f.from_country_id === aId ? f.from_country_name : f.to_country_name;
        const bName = f.to_country_id === bId ? f.to_country_name : f.from_country_name;
        // fee goes from buyer (to_country) to seller (from_country)
        // Convention: positive netFee = money flows A→B (A is buyer)
        const net = f.from_country_id === aId ? -f.total_fee_eur : f.total_fee_eur;
        netFlowMap.set(key, {
          countryA_id: aId, countryA_name: aName,
          countryB_id: bId, countryB_name: bName,
          netFee: net, totalTransfers: f.transfer_count,
        });
      }
    }

    const maxNetFee = Math.max(...Array.from(netFlowMap.values()).map((f) => Math.abs(f.netFee)), 1);
    const netFlowThreshold = maxNetFee * 0.005;

    const arcData = Array.from(netFlowMap.values())
      .filter((f) => Math.abs(f.netFee) >= netFlowThreshold)
      .map((f) => {
        // Arc goes from spender to receiver (direction of money)
        const spenderId = f.netFee >= 0 ? f.countryA_id : f.countryB_id;
        const receiverId = f.netFee >= 0 ? f.countryB_id : f.countryA_id;
        const spenderName = f.netFee >= 0 ? f.countryA_name : f.countryB_name;
        const receiverName = f.netFee >= 0 ? f.countryB_name : f.countryA_name;
        const spender = countryById.get(spenderId);
        const receiver = countryById.get(receiverId);
        if (!spender || !receiver) return null;
        return {
          fromPos: [spender.longitude, spender.latitude] as [number, number],
          toPos: [receiver.longitude, receiver.latitude] as [number, number],
          fee: Math.abs(f.netFee),
          spenderName,
          receiverName,
          totalTransfers: f.totalTransfers,
        };
      })
      .filter(Boolean) as {
        fromPos: [number, number]; toPos: [number, number];
        fee: number; spenderName: string; receiverName: string; totalTransfers: number;
      }[];

    const maxLogFee = Math.log10(Math.max(maxNetFee, 1));

    const arcLayer = new ArcLayer({
      id: "flow-arcs",
      data: arcData,
      getSourcePosition: (d) => d.fromPos,
      getTargetPosition: (d) => d.toPos,
      getSourceColor: [239, 68, 68, 178],  // red (spender end)
      getTargetColor: [34, 197, 94, 178],   // green (receiver end)
      getWidth: (d) => {
        const logFee = Math.log10(Math.max(d.fee, 1));
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
            fromCountry: info.object.spenderName,
            toCountry: info.object.receiverName,
            fee: info.object.fee,
            transferCount: info.object.totalTransfers,
          });
        } else {
          setTooltip(null);
        }
      },
      updateTriggers: {
        getWidth: [maxNetFee],
      },
    });

    return [arcLayer, scatterLayer];
  }, [countries, flows, countrySummaries, countryTransferTotals, maxVolume, maxAbsNetSpend, maxFlowFee, countryById, summaryById, onSelectCountry]);

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
