import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import { formatFee, formatCount } from "@/lib/format";
import { getFlag } from "@/lib/flags";
import { Spinner } from "@/components/atoms/Spinner";
import { EmptyState } from "@/components/molecules/EmptyState";
import type { ClubNetworkResponse, ClubNetworkExpandResponse } from "@/types/api";

interface NetworkGraphProps {
  networkData: ClubNetworkResponse | null;
  expandedData: Map<number, ClubNetworkExpandResponse>;
  expandedCountries: Set<number>;
  isLoading: boolean;
  onExpandCountry: (countryId: number) => void;
  onCollapseCountry: (countryId: number) => void;
  onRecenter: (clubId: number) => void;
}

interface GraphNode {
  id: string;
  type: "center" | "country" | "club";
  label: string;
  radius: number;
  color: string;
  countryId?: number;
  clubId?: number;
  isoCode?: string;
  expanded?: boolean;
  // Tooltip data
  totalSpent?: number;
  totalReceived?: number;
  transferCount?: number;
}

interface GraphLink {
  source: string;
  target: string;
  width: number;
  color: string;
}

/** Force-directed network graph for club transfer relationships. */
export function NetworkGraph({
  networkData,
  expandedData,
  expandedCountries,
  isLoading,
  onExpandCountry,
  onCollapseCountry,
  onRecenter,
}: NetworkGraphProps) {
  const graphRef = useRef<any>(null); // eslint-disable-line @typescript-eslint/no-explicit-any
  const [tooltip, setTooltip] = useState<{ x: number; y: number; content: string } | null>(null);

  // Build graph data
  const { nodes, links } = useMemo(() => {
    if (!networkData) return { nodes: [] as GraphNode[], links: [] as GraphLink[] };

    const nodes: GraphNode[] = [];
    const links: GraphLink[] = [];

    const maxVolume = Math.max(
      ...networkData.country_edges.map((e) => e.total_spent_eur + e.total_received_eur),
      1,
    );
    const maxLogVolume = Math.log10(maxVolume);

    // Center club
    nodes.push({
      id: `club-${networkData.center_club.club_id}`,
      type: "center",
      label: networkData.center_club.club_name,
      radius: 30,
      color: "#4ade80",
      clubId: networkData.center_club.club_id,
    });

    // Country nodes
    for (const edge of networkData.country_edges) {
      const volume = edge.total_spent_eur + edge.total_received_eur;
      const normalizedSize = Math.sqrt(volume / maxVolume);
      const isExpanded = expandedCountries.has(edge.country_id);

      nodes.push({
        id: `country-${edge.country_id}`,
        type: "country",
        label: edge.country_name,
        radius: 15 + normalizedSize * 25,
        color: "#6b7280",
        countryId: edge.country_id,
        expanded: isExpanded,
        totalSpent: edge.total_spent_eur,
        totalReceived: edge.total_received_eur,
        transferCount: edge.transfer_count,
      });

      const netSpend = edge.total_spent_eur - edge.total_received_eur;
      const logWidth = Math.log10(Math.max(volume, 1)) / maxLogVolume;

      links.push({
        source: `club-${networkData.center_club.club_id}`,
        target: `country-${edge.country_id}`,
        width: 1 + logWidth * 8,
        color: netSpend > 0 ? "rgba(239, 68, 68, 0.6)" : "rgba(34, 197, 94, 0.6)",
      });

      // Expanded club nodes
      if (isExpanded) {
        const expanded = expandedData.get(edge.country_id);
        if (expanded) {
          for (const clubEdge of expanded.club_edges) {
            const clubVol = clubEdge.total_spent_eur + clubEdge.total_received_eur;
            const clubNorm = Math.sqrt(clubVol / maxVolume);
            const clubNetSpend = clubEdge.total_spent_eur - clubEdge.total_received_eur;

            nodes.push({
              id: `expanded-${clubEdge.club_id}`,
              type: "club",
              label: clubEdge.club_name,
              radius: 10 + clubNorm * 15,
              color: clubNetSpend > 0 ? "#ef4444" : "#22c55e",
              clubId: clubEdge.club_id,
              totalSpent: clubEdge.total_spent_eur,
              totalReceived: clubEdge.total_received_eur,
              transferCount: clubEdge.transfer_count,
            });

            const clubLogWidth = Math.log10(Math.max(clubVol, 1)) / maxLogVolume;
            links.push({
              source: `country-${edge.country_id}`,
              target: `expanded-${clubEdge.club_id}`,
              width: 1 + clubLogWidth * 6,
              color: clubNetSpend > 0 ? "rgba(239, 68, 68, 0.4)" : "rgba(34, 197, 94, 0.4)",
            });
          }
        }
      }
    }

    return { nodes, links };
  }, [networkData, expandedData, expandedCountries]);

  // Configure forces and fit view when graph data changes
  useEffect(() => {
    const fg = graphRef.current;
    if (!fg) return;
    fg.d3Force("charge")?.strength(-500);
    fg.d3Force("link")?.distance(250);
    fg.d3Force("center")?.strength(1);
    fg.d3ReheatSimulation();
    // Fit all nodes in view after simulation settles
    const timer = setTimeout(() => {
      fg.zoomToFit(400, 80);
    }, 1000);
    return () => clearTimeout(timer);
  }, [nodes.length]);

  // Custom node rendering
  const paintNode = useCallback((node: GraphNode, ctx: CanvasRenderingContext2D) => {
    const x = (node as any).x ?? 0; // eslint-disable-line @typescript-eslint/no-explicit-any
    const y = (node as any).y ?? 0; // eslint-disable-line @typescript-eslint/no-explicit-any
    const r = node.radius;

    // Circle
    ctx.beginPath();
    ctx.arc(x, y, r, 0, 2 * Math.PI);
    ctx.fillStyle = node.color;
    ctx.fill();

    if (node.type === "center") {
      ctx.strokeStyle = "#ffffff";
      ctx.lineWidth = 2;
      ctx.stroke();
    }

    // Label
    const fontSize = node.type === "center" ? 12 : node.type === "country" ? 10 : 8;
    ctx.font = `${fontSize}px Inter, sans-serif`;
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    ctx.fillStyle = "#e8f0ec";
    ctx.fillText(node.label, x, y + r + 4);

    // Expansion indicator for country nodes
    if (node.type === "country") {
      const indicatorR = 6;
      const ix = x + r * 0.7;
      const iy = y - r * 0.7;
      ctx.beginPath();
      ctx.arc(ix, iy, indicatorR, 0, 2 * Math.PI);
      ctx.fillStyle = "#1e3a2a";
      ctx.fill();
      ctx.strokeStyle = "#8fa898";
      ctx.lineWidth = 1;
      ctx.stroke();
      ctx.fillStyle = "#e8f0ec";
      ctx.font = "bold 10px Inter, sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(node.expanded ? "−" : "+", ix, iy);
    }
  }, []);

  // Click handler
  const handleNodeClick = useCallback((node: GraphNode) => {
    if (node.type === "country" && node.countryId !== undefined) {
      if (expandedCountries.has(node.countryId)) {
        onCollapseCountry(node.countryId);
      } else {
        onExpandCountry(node.countryId);
      }
    } else if (node.type === "club" && node.clubId !== undefined) {
      onRecenter(node.clubId);
    }
  }, [expandedCountries, onExpandCountry, onCollapseCountry, onRecenter]);

  // Hover handler
  const handleNodeHover = useCallback((node: GraphNode | null, event?: MouseEvent) => {
    if (!node || node.type === "center") {
      setTooltip(null);
      return;
    }
    setTooltip({
      x: event?.clientX ?? 0,
      y: event?.clientY ?? 0,
      content: `${node.label}\nSpent: ${formatFee(node.totalSpent ?? 0)}\nReceived: ${formatFee(node.totalReceived ?? 0)}\n${formatCount(node.transferCount ?? 0)} transfers`,
    });
  }, []);

  if (isLoading && !networkData) {
    return (
      <div style={{ width: "100%", height: "100%" }} className="flex items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  if (!networkData || networkData.country_edges.length === 0) {
    return (
      <div style={{ width: "100%", height: "100%" }} className="flex items-center justify-center">
        <EmptyState message={networkData ? "No transfers found for this club with the current filters" : "Search for a club to explore its transfer network"} />
      </div>
    );
  }

  return (
    <div style={{ width: "100%", height: "100%" }}>
      <ForceGraph2D
        ref={graphRef}
        graphData={{ nodes, links }}
        nodeId="id"
        nodeCanvasObject={paintNode}
        nodePointerAreaPaint={(node: GraphNode, color: string, ctx: CanvasRenderingContext2D) => {
          const x = (node as any).x ?? 0; // eslint-disable-line @typescript-eslint/no-explicit-any
          const y = (node as any).y ?? 0; // eslint-disable-line @typescript-eslint/no-explicit-any
          ctx.beginPath();
          ctx.arc(x, y, node.radius, 0, 2 * Math.PI);
          ctx.fillStyle = color;
          ctx.fill();
        }}
        linkWidth={(link: GraphLink) => link.width}
        linkColor={(link: GraphLink) => link.color}
        onNodeClick={handleNodeClick}
        onNodeHover={handleNodeHover}
        backgroundColor="#0f1a14"
        d3AlphaDecay={0.02}
        d3VelocityDecay={0.25}
        cooldownTicks={200}
        nodeRelSize={1}
      />

      {tooltip && (
        <div
          className="pointer-events-none fixed z-50 rounded-lg bg-[#1e3a2a] border border-[#2d4a38] px-3 py-2 shadow-lg text-sm whitespace-pre-line"
          style={{ left: tooltip.x + 12, top: tooltip.y - 12 }}
        >
          <span className="text-[#e8f0ec]">{tooltip.content}</span>
        </div>
      )}

      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/20 pointer-events-none">
          <Spinner size="lg" />
        </div>
      )}
    </div>
  );
}
