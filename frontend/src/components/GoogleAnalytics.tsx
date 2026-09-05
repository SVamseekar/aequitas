import { useEffect } from "react"
import { useLocation } from "react-router"

const GA_MEASUREMENT_ID =
  import.meta.env.NEXT_PUBLIC_GA_MEASUREMENT_ID?.trim() || "G-MWQL8XNKTE"

declare global {
  interface Window {
    dataLayer: unknown[]
    gtag?: (...args: unknown[]) => void
  }
}

function ensureGtag() {
  if (!import.meta.env.PROD || !GA_MEASUREMENT_ID) return
  if (typeof window.gtag === "function") return

  window.dataLayer = window.dataLayer || []
  window.gtag = function gtag() {
    window.dataLayer.push(arguments)
  }

  const src = `https://www.googletagmanager.com/gtag/js?id=${GA_MEASUREMENT_ID}`
  if (!document.querySelector(`script[src="${src}"]`)) {
    const script = document.createElement("script")
    script.async = true
    script.src = src
    document.head.appendChild(script)
  }

  window.gtag("js", new Date())
  window.gtag("config", GA_MEASUREMENT_ID, {
    anonymize_ip: true,
    send_page_view: false,
  })
}

export function GoogleAnalytics() {
  const location = useLocation()

  useEffect(() => {
    ensureGtag()
  }, [])

  useEffect(() => {
    if (!import.meta.env.PROD || typeof window.gtag !== "function") return
    window.gtag("event", "page_view", {
      page_path: location.pathname + location.search,
      page_location: window.location.href,
      page_title: document.title,
    })
  }, [location.pathname, location.search])

  return null
}
