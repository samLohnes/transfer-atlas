/** Map ISO codes to flag emoji. Custom codes for England/Scotland. */
const FLAG_MAP: Record<string, string> = {
  ENG: "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
  SCO: "🏴󠁧󠁢󠁳󠁣󠁴󠁿",
};

/** Get flag emoji for a country ISO code. */
export function getFlag(isoCode: string): string {
  if (FLAG_MAP[isoCode]) return FLAG_MAP[isoCode];
  // Standard ISO 3166-1 alpha-2 derived from alpha-3
  // Regional indicator symbols: A=🇦 (U+1F1E6), etc.
  const alpha2 = isoCodeToAlpha2(isoCode);
  if (!alpha2) return "🏳️";
  return String.fromCodePoint(
    ...alpha2.split("").map((c) => 0x1f1e6 + c.charCodeAt(0) - 65)
  );
}

const ALPHA3_TO_ALPHA2: Record<string, string> = {
  ARG: "AR", BEL: "BE", BRA: "BR", DEU: "DE", ESP: "ES",
  FRA: "FR", ITA: "IT", NLD: "NL", PRT: "PT", TUR: "TR",
};

function isoCodeToAlpha2(alpha3: string): string | null {
  return ALPHA3_TO_ALPHA2[alpha3] ?? null;
}
