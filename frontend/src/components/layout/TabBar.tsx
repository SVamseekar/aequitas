import { NavLink, useSearchParams } from "react-router"
import { dimensionsForCountry } from "@/lib/constants"
import { useFilters } from "@/api/hooks"
import { appHome, appPath, withSearch } from "@/lib/appRoutes"

export function TabBar() {
  const { country } = useFilters()
  const dims = dimensionsForCountry(country)
  const [params] = useSearchParams()
  const search = params.toString()
  const link = (path: string) => withSearch(path, search)
  return (
    <nav className="app-glass-bar border-b sticky top-14 z-20">
      <div className="mx-auto max-w-7xl px-4 flex gap-0.5 flex-wrap overflow-x-auto">
        <NavLink
          to={link(appHome(country))}
          end
          className={({ isActive }) =>
            `px-3 py-2.5 text-sm whitespace-nowrap border-b-2 transition-colors ${
              isActive
                ? "border-primary text-primary font-semibold"
                : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
            }`
          }
        >
          Home
        </NavLink>
        {dims.map((d) => (
          <NavLink
            key={d.id}
            to={link(appPath(country, d.route.slice(1)))}
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
          to={link(appPath(country, "time"))}
          className={({ isActive }) =>
            `px-3 py-2.5 text-sm whitespace-nowrap border-b-2 transition-colors ${
              isActive
                ? "border-primary text-primary font-semibold"
                : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
            }`
          }
        >
          Time
        </NavLink>
        <NavLink
          to={link(appPath(country, "reach"))}
          className={({ isActive }) =>
            `px-3 py-2.5 text-sm whitespace-nowrap border-b-2 transition-colors ${
              isActive
                ? "border-primary text-primary font-semibold"
                : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
            }`
          }
        >
          Reach
        </NavLink>
        <NavLink
          to={link(appPath(country, "studio"))}
          className={({ isActive }) =>
            `px-3 py-2.5 text-sm whitespace-nowrap border-b-2 transition-colors ${
              isActive
                ? "border-primary text-primary font-semibold"
                : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
            }`
          }
        >
          Studio
        </NavLink>
        <NavLink
          to={link(appPath(country, "compare"))}
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
