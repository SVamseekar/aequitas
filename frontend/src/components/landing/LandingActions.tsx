import { Link } from "react-router"

/** Conveyal pair: outline Learn more + filled primary. One pair per page close. */
export function LandingActions({
  primaryTo = "/briefings",
  primary = "Read the briefings",
  secondaryTo = "/methodology",
  secondary = "Learn more",
}: {
  primaryTo?: string
  primary?: string
  secondaryTo?: string
  secondary?: string
}) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <Link to={secondaryTo} className="landing-btn-secondary">
        {secondary}
      </Link>
      <Link to={primaryTo} className="landing-btn-primary">
        {primary}
      </Link>
    </div>
  )
}
