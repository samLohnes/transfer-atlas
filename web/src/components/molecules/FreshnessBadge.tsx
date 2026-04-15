import { useEffect, useState } from "react";
import { fetchMetadata } from "@/lib/api";
import { Badge } from "@/components/atoms/Badge";

/** Displays data freshness from pipeline metadata. Turns amber if data > 45 days old. */
export function FreshnessBadge() {
  const [label, setLabel] = useState<string | null>(null);
  const [isStale, setIsStale] = useState(false);

  useEffect(() => {
    fetchMetadata()
      .then((meta) => {
        const date = new Date(meta.last_ingestion_at);
        const formatted = date.toLocaleDateString("en-US", {
          month: "short",
          day: "numeric",
          year: "numeric",
        });
        setLabel(`Data updated: ${formatted}`);

        const daysSince = (Date.now() - date.getTime()) / (1000 * 60 * 60 * 24);
        setIsStale(daysSince > 45);
      })
      .catch(() => setLabel("Data: unknown"));
  }, []);

  if (!label) return null;

  return (
    <Badge variant={isStale ? "warning" : "default"}>
      {label}
    </Badge>
  );
}
