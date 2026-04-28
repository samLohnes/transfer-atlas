/** Predefined fee breakpoints (EUR, not cents) used by the Map FilterBar
 *  and the Grades page fee filter. Indices map cleanly to slider positions
 *  and to <option> values. */
export const FEE_STEPS_EUR: readonly number[] = [
  0, 500_000, 1_000_000, 2_000_000, 5_000_000, 10_000_000,
  15_000_000, 20_000_000, 30_000_000, 50_000_000, 75_000_000,
  100_000_000, 150_000_000, 200_000_000, 250_000_000,
] as const;
