import { Link, useSearchParams } from "react-router"
import { useFilters } from "@/api/hooks"
import { appHome, withSearch } from "@/lib/appRoutes"
import { FilterDropdowns } from "./FilterDropdowns"
import { UserMenu } from "./UserMenu"
import { TenantSwitcher } from "./TenantSwitcher"
import { AequitasLogo } from "../shared/AequitasLogo"

export function Header() {
  const { country } = useFilters()
  const [params] = useSearchParams()
  return (
    <header className="app-glass-bar sticky top-0 z-30 border-b">
      <div className="mx-auto max-w-7xl px-4 h-14 flex items-center justify-between gap-4">
        <Link
          to={withSearch(appHome(country), params.toString())}
          className="flex items-center gap-2.5 text-sm font-semibold text-foreground hover:text-primary transition-colors shrink-0"
        >
          <span className="app-glass flex h-8 w-8 items-center justify-center rounded-xl">
            <AequitasLogo className="w-4 h-4 text-primary" />
          </span>
          <span>
            Aequitas
            <span className="hidden sm:inline text-muted-foreground font-normal">
              {" "}
              · Policy intelligence
            </span>
          </span>
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
