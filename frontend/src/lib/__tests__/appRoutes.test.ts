import { describe, expect, it } from "vitest"
import { legacyDashboardToApp, productSlugOrNull, withSearch } from "../appRoutes"

describe("legacyDashboardToApp", () => {
  it("sends dashboard home to England app", () => {
    expect(legacyDashboardToApp("/dashboard", "")).toBe("/app/england")
  })

  it("maps old accessibility slug", () => {
    expect(legacyDashboardToApp("/dashboard/accessibility", "?region=all")).toBe(
      "/app/england/access?region=all",
    )
  })

  it("maps compare", () => {
    expect(legacyDashboardToApp("/dashboard/compare", "")).toBe("/app/england/compare")
  })

  it("maps reach as its own slug", () => {
    expect(legacyDashboardToApp("/dashboard/reach", "?region=all")).toBe("/app/england/reach?region=all")
  })

  it("preserves filter query on in-app links", () => {
    expect(withSearch("/app/england/equity", "region=E12000007&urban_rural=urban")).toEqual({
      pathname: "/app/england/equity",
      search: "?region=E12000007&urban_rural=urban",
    })
  })

  it("drops E12 and compare leftovers on Ireland paths", () => {
    expect(withSearch("/app/ireland/reach", "region=E12000005&urban_rural=rural&a=x&franchise=1")).toEqual({
      pathname: "/app/ireland/reach",
      search: "?region=all&urban_rural=rural",
    })
  })

  it("maps warehouse slugs to product doors", () => {
    expect(productSlugOrNull("economic")).toBe("economy")
    expect(productSlugOrNull("accessibility")).toBe("access")
    expect(productSlugOrNull("service_quality")).toBe("service")
    expect(productSlugOrNull("route_network")).toBe("network")
    expect(productSlugOrNull("bus_services_act")).toBe("policy")
    expect(productSlugOrNull("economy")).toBeNull()
    expect(productSlugOrNull("time")).toBeNull()
  })

  it("keeps pack when redirecting a warehouse slug", () => {
    expect(withSearch("/app/ireland/economy", "region=cork&urban_rural=rural&pack=2099-01-01")).toEqual({
      pathname: "/app/ireland/economy",
      search: "?region=cork&urban_rural=rural&pack=2099-01-01",
    })
  })

  it("keeps pack on in-country moves", () => {
    expect(withSearch("/app/england/time", "region=E12000005&urban_rural=urban&pack=2026-08-01")).toEqual({
      pathname: "/app/england/time",
      search: "?region=E12000005&urban_rural=urban&pack=2026-08-01",
    })
  })
})
