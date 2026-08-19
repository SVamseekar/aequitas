import { useLayoutEffect } from "react"
import { useLocation } from "react-router"

/** New routes start at the top. Hash links wait for the target (lazy pages). */
export function ScrollToTop() {
  const { pathname, hash } = useLocation()

  useLayoutEffect(() => {
    if (!hash) {
      window.scrollTo({ top: 0, left: 0, behavior: "auto" })
      return
    }

    let cancelled = false
    const id = decodeURIComponent(hash.replace(/^#/, ""))

    const jump = (attempt: number) => {
      if (cancelled) return
      const el = document.getElementById(id)
      if (el) {
        el.scrollIntoView({ block: "start", behavior: "auto" })
        return
      }
      if (attempt < 24) requestAnimationFrame(() => jump(attempt + 1))
      else window.scrollTo({ top: 0, left: 0, behavior: "auto" })
    }

    jump(0)
    return () => {
      cancelled = true
    }
  }, [pathname, hash])

  return null
}
