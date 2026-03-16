import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { REGIONS, AREA_TYPES } from "@/lib/constants"
import { useFilters } from "@/api/hooks"

export function FilterDropdowns() {
  const { region, urbanRural, setRegion, setUrbanRural } = useFilters()

  return (
    <div className="flex gap-2">
      <Select value={region} onValueChange={(v: string | null) => { if (v !== null) setRegion(v) }}>
        <SelectTrigger className="w-[180px] bg-white/10 border-white/20 text-white text-sm">
          <SelectValue placeholder="Region" />
        </SelectTrigger>
        <SelectContent>
          {REGIONS.map((r) => (
            <SelectItem key={r.code} value={r.code}>{r.name}</SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Select value={urbanRural} onValueChange={(v: string | null) => { if (v !== null) setUrbanRural(v) }}>
        <SelectTrigger className="w-[130px] bg-white/10 border-white/20 text-white text-sm">
          <SelectValue placeholder="Area type" />
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
