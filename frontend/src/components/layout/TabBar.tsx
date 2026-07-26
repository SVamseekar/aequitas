import { NavLink } from "react-router"
import { DIMENSIONS } from "@/lib/constants"

export function TabBar() {
  return (
    <nav className="app-glass-bar border-b sticky top-14 z-20">
      <div className="mx-auto max-w-7xl px-4 flex gap-0.5 flex-wrap overflow-x-auto">
        {DIMENSIONS.map((d) => (
          <NavLink
            key={d.id}
            to={d.route.slice(1)}
            className={({ isActive }) =>
              `px-3 py-2.5 text-sm whitespace-nowrap border-b-2 transition-colors ${
                isActive
                  ? "border-primary text-primary font-semibold"
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
            `px-3 py-2.5 text-sm whitespace-nowrap border-b-2 transition-colors ${
              isActive
                ? "border-primary text-primary font-semibold"
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
