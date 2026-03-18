import { Link } from "react-router"
import { FilterDropdowns } from "./FilterDropdowns"
import { UserMenu } from "./UserMenu"

export function Header() {
  return (
    <header className="border-b border-border bg-card/50">
      <div className="mx-auto max-w-7xl px-4 h-14 flex items-center justify-between">
        <Link
          to="/dashboard"
          className="flex items-center gap-2.5 text-sm font-mono font-bold tracking-widest uppercase text-foreground hover:text-indigo-400 transition-colors"
        >
          AEQUITAS
        </Link>
        <div className="flex items-center gap-4">
          <FilterDropdowns />
          <UserMenu />
        </div>
      </div>
    </header>
  )
}
