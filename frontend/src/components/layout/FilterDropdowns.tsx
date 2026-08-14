import { Select, SelectContent, SelectItem, SelectTrigger } from "@/components/ui/select"
import { COUNTRIES, AREA_TYPES, regionsForCountry } from "@/lib/constants"
import { useFilters, usePackDates } from "@/api/hooks"

export function FilterDropdowns() {
  const { country, region, urbanRural, pack, mode, setCountry, setRegion, setUrbanRural, setPack, setMode } =
    useFilters()

  const packsQ = usePackDates()
  const dates = (packsQ.data?.[country as "england" | "ireland"]?.dates ?? []) as {
    pack_id: string
    as_of: string
    current?: boolean
  }[]
  const packValue = pack || dates.find((d) => d.current)?.pack_id || "current"
  const packLabel =
    dates.find((d) => d.pack_id === packValue)?.as_of ??
    (packValue === "current" ? "Current pack" : packValue)

  const countryName = COUNTRIES.find((c) => c.code === country)?.name ?? "Country"
  const packReady = COUNTRIES.find((c) => c.code === country)?.packReady ?? false
  const regionOptions = regionsForCountry(country)
  const regionName = regionOptions.find((r) => r.code === region)?.name ?? regionOptions[0]?.name ?? "Region"
  const areaName = AREA_TYPES.find((a) => a.code === urbanRural)?.name ?? "Area type"

  return (
    <div className="flex gap-2">
      <Select value={country} onValueChange={(v: string | null) => { if (v !== null) setCountry(v) }}>
        <SelectTrigger className="w-[130px] sm:w-[150px] app-glass border-white/50 text-foreground text-sm rounded-xl h-9">
          <span className="flex flex-1 text-left truncate">{countryName}</span>
        </SelectTrigger>
        <SelectContent className="app-glass-strong">
          {COUNTRIES.map((c) => (
            <SelectItem key={c.code} value={c.code}>
              {c.name}{c.packReady ? "" : " (soon)"}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Select
        value={packReady ? region : "all"}
        onValueChange={(v: string | null) => {
          if (v !== null && packReady) setRegion(v)
        }}
      >
        <SelectTrigger className="w-[160px] sm:w-[180px] app-glass border-white/50 text-foreground text-sm rounded-xl h-9">
          <span className="flex flex-1 text-left truncate">{regionName}</span>
        </SelectTrigger>
        <SelectContent className="app-glass-strong">
          {regionOptions.map((r) => (
            <SelectItem key={r.code} value={r.code}>
              {r.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Select
        value={urbanRural}
        onValueChange={(v: string | null) => {
          if (v !== null) setUrbanRural(v)
        }}
      >
        <SelectTrigger className="w-[120px] sm:w-[130px] app-glass border-white/50 text-foreground text-sm rounded-xl h-9">
          <span className="flex flex-1 text-left truncate">{areaName}</span>
        </SelectTrigger>
        <SelectContent className="app-glass-strong">
          {AREA_TYPES.map((a) => (
            <SelectItem key={a.code} value={a.code}>
              {a.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {country === "netherlands" && packReady ? (
        <Select value={mode} onValueChange={(v: string | null) => { if (v !== null) setMode(v) }}>
          <SelectTrigger className="w-[140px] sm:w-[160px] app-glass border-white/50 text-foreground text-sm rounded-xl h-9">
            <span className="flex flex-1 text-left truncate">{mode === "all" ? "All public transport" : "Bus only"}</span>
          </SelectTrigger>
          <SelectContent className="app-glass-strong">
            <SelectItem value="bus">Bus only</SelectItem>
            <SelectItem value="all">All public transport</SelectItem>
          </SelectContent>
        </Select>
      ) : null}
      {packReady && dates.length > 0 ? (
        <Select
          value={packValue}
          onValueChange={(v: string | null) => {
            if (v !== null) setPack(v)
          }}
        >
          <SelectTrigger className="w-[130px] sm:w-[150px] app-glass border-white/50 text-foreground text-sm rounded-xl h-9">
            <span className="flex flex-1 text-left truncate">{packLabel}</span>
          </SelectTrigger>
          <SelectContent className="app-glass-strong">
            {dates.map((d) => (
              <SelectItem key={d.pack_id} value={d.pack_id}>
                {d.as_of}
                {d.current ? " (current)" : ""}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      ) : null}
    </div>
  )
}
