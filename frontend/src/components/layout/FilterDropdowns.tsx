import { Select, SelectContent, SelectItem, SelectTrigger } from "@/components/ui/select"
import { REGIONS, AREA_TYPES } from "@/lib/constants"
import { useFilters } from "@/api/hooks"

export function FilterDropdowns() {
  const { region, urbanRural, setRegion, setUrbanRural } = useFilters()

  const regionName = REGIONS.find((r) => r.code === region)?.name ?? "Region"
  const areaName = AREA_TYPES.find((a) => a.code === urbanRural)?.name ?? "Area type"

  return (
    <div className="flex gap-2">
      <Select value={region} onValueChange={(v: string | null) => { if (v !== null) setRegion(v) }}>
        <SelectTrigger className="w-[180px] bg-input border-border text-foreground text-sm">
          <span className="flex flex-1 text-left truncate">{regionName}</span>
        </SelectTrigger>
        <SelectContent>
          {REGIONS.map((r) => (
            <SelectItem key={r.code} value={r.code}>{r.name}</SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Select value={urbanRural} onValueChange={(v: string | null) => { if (v !== null) setUrbanRural(v) }}>
        <SelectTrigger className="w-[130px] bg-input border-border text-foreground text-sm">
          <span className="flex flex-1 text-left truncate">{areaName}</span>
        </SelectTrigger>
        <SelectContent>
          {AREA_TYPES.map((a) => (
            <SelectItem key={a.code} value={a.code}>{a.name}</SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}
