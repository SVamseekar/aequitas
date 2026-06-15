import { NavLink } from "react-router"
import { DIMENSIONS } from "@/lib/constants"

export function TabBar() {
  return (
    <nav className="border-b border-border bg-card/30">
      <div className="mx-auto max-w-7xl px-4 flex gap-0 flex-wrap justify-between">
        {DIMENSIONS.map((d) => (
          <NavLink
            key={d.id}
            to={d.route.slice(1)}
            className={({ isActive }) =>
              `px-2 py-2.5 text-[11px] font-mono uppercase tracking-wide whitespace-nowrap border-b-2 transition-colors ${
                isActive
                  ? "border-indigo-500 text-indigo-400"
                  : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
              }`
            }
          >
            {d.name}
          </NavLink>
        ))}
        <NavLink
          to="compare"
          className={({ isActive }) =>
            `px-2 py-2.5 text-[11px] font-mono uppercase tracking-wide whitespace-nowrap border-b-2 transition-colors ${
              isActive
                ? "border-indigo-500 text-indigo-400"
                : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
            }`
          }
        >
          Compare
        </NavLink>
      </div>
    </nav>
  )
}
