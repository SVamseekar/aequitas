import { Link } from "react-router"
import { FilterDropdowns } from "./FilterDropdowns"
import { UserMenu } from "./UserMenu"

export function Header() {
  return (
    <header className="bg-[#1a1a2e] text-white">
      <div className="mx-auto max-w-7xl px-4 py-3 flex items-center justify-between">
        <Link to="/" className="text-xl font-semibold tracking-tight">
          Aequitas
        </Link>
        <div className="flex items-center gap-4">
          <FilterDropdowns />
          <UserMenu />
        </div>
      </div>
    </header>
  )
}
