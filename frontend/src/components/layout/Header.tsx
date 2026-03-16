import { Link } from "react-router"
import { FilterDropdowns } from "./FilterDropdowns"

export function Header() {
  return (
    <header className="bg-[#1a1a2e] text-white">
      <div className="mx-auto max-w-7xl px-4 py-3 flex items-center justify-between">
        <Link to="/" className="text-xl font-semibold tracking-tight">
          Aequitas
        </Link>
        <FilterDropdowns />
      </div>
    </header>
  )
}
