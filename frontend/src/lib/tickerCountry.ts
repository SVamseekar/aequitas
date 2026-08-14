export type TickerChip = {
  key: string
  label: string
  value: string
  sub: string
}

/** Empty / unknown-pack chips. Never name another country’s live pack. */
export function tickerForUnknownPack(country: string): TickerChip[] {
  const label =
    country === "ireland"
      ? "Ireland"
      : country === "england"
        ? "England"
        : country === "netherlands"
          ? "Netherlands"
          : country === "france"
            ? "France"
            : country
  return [
    {
      key: "pack",
      label,
      value: "empty",
      sub: "unknown network date",
    },
  ]
}
