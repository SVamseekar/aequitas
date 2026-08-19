import type { ReactNode } from "react"
import { LandingNav } from "@/components/landing/LandingNav"
import { LandingFooter } from "@/components/landing/LandingFooter"

export function BriefingLayout({ children }: { children: ReactNode }) {
  return (
    <div className="landing-root min-h-screen">
      <LandingNav />
      <main id="main-content" className="landing-shell py-12 sm:py-14">
        {children}
      </main>
      <LandingFooter />
    </div>
  )
}
