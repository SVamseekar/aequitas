import { Link, useSearchParams } from "react-router"
import { useFilters } from "@/api/hooks"
import { appHome, withSearch } from "@/lib/appRoutes"
import { FilterDropdowns } from "./FilterDropdowns"
import { UserMenu } from "./UserMenu"
import { TenantSwitcher } from "./TenantSwitcher"
import { AequitasLockup } from "../shared/AequitasLockup"

export function Header() {
  const { country } = useFilters()
  const [params] = useSearchParams()
  return (
    <header className="app-glass-bar sticky top-0 z-30 border-b">
      <div className="mx-auto max-w-7xl px-4 h-14 flex items-center justify-between gap-4">
        <Link
          to={withSearch(appHome(country), params.toString())}
          className="shrink-0 hover:opacity-80 transition-opacity"
        >
          <AequitasLockup size="nav" />
        </Link>
        <div className="flex items-center gap-3 sm:gap-4 min-w-0">
          <FilterDropdowns />
          <TenantSwitcher />
          <UserMenu />
        </div>
      </div>
    </header>
  )
}
