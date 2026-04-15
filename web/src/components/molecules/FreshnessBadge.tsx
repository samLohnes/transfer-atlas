import { useEffect, useState } from "react";
import { fetchMetadata } from "@/lib/api";
import { Badge } from "@/components/atoms/Badge";

/** Displays data freshness from pipeline metadata. Turns amber if data > 45 days old. */
export function FreshnessBadge() {
  const [label, setLabel] = useState<string | null>(null);
  const [variant, setVariant] = useState<"default" | "warning">("default");

  useEffect(() => {
    fetchMetadata()
      .then((meta) => {
        const date = new Date(meta.last_ingestion_at);
        const formatted = date.toLocaleDateString("en-US", {
          month: "short",
          day: "numeric",
          year: "numeric",
        });
        setLabel(`Updated: ${formatted}`);

        const daysSince = (Date.now() - date.getTime()) / (1000 * 60 * 60 * 24);
        setVariant(daysSince > 45 ? "warning" : "default");
      })
      .catch((err) => {
        if (err.message.includes("404")) {
          setLabel("No data loaded");
          setVariant("warning");
        } else {
          setLabel("Data: unavailable");
          setVariant("warning");
        }
      });
  }, []);

  if (!label) return null;

  return <Badge variant={variant}>{label}</Badge>;
}
