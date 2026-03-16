import { NavLink } from "react-router"
import { DIMENSIONS } from "@/lib/constants"

export function TabBar() {
  return (
    <nav className="border-b bg-white">
      <div className="mx-auto max-w-7xl px-4 flex gap-0 overflow-x-auto">
        {DIMENSIONS.map((d) => (
          <NavLink
            key={d.id}
            to={d.route}
            className={({ isActive }) =>
              `px-4 py-3 text-sm whitespace-nowrap border-b-2 transition-colors ${
                isActive
                  ? "border-indigo-500 text-indigo-600 font-medium"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
              }`
            }
          >
            {d.name}
          </NavLink>
        ))}
      </div>
    </nav>
  )
}
