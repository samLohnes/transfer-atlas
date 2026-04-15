/**
 * Format a fee in EUR cents to a human-readable string.
 * 7500000000 → "€75M", 150000000 → "€1.5M", 50000000 → "€500K", 0 → "Free", null → "Undisclosed"
 */
export function formatFee(eurCents: number | null): string {
  if (eurCents === null || eurCents === undefined) return "Undisclosed";
  if (eurCents === 0) return "Free";

  const eur = eurCents / 100;

  if (eur >= 1_000_000) {
    const millions = eur / 1_000_000;
    return millions % 1 === 0 ? `€${millions}M` : `€${millions.toFixed(1)}M`;
  }
  if (eur >= 1_000) {
    const thousands = eur / 1_000;
    return thousands % 1 === 0 ? `€${thousands}K` : `€${thousands.toFixed(1)}K`;
  }
  return `€${eur.toLocaleString()}`;
}

/** Format a number with locale-aware thousands separator. */
export function formatCount(n: number): string {
  return n.toLocaleString();
}

/** Format a date string to "Jul 15, 2023" format. */
export function formatDate(dateStr: string): string {
  const date = new Date(dateStr + "T00:00:00");
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}
