import { FilterDropdowns } from "./FilterDropdowns"
import { UserMenu } from "./UserMenu"
import { TenantSwitcher } from "./TenantSwitcher"

export function Header() {
  return (
    <header className="app-context-bar">
        <div className="flex items-center justify-between gap-3 w-full min-w-0">
          <FilterDropdowns />
          <TenantSwitcher />
          <UserMenu />
        </div>
    </header>
  )
}
