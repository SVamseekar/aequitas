import { Component, useState, type ReactNode } from "react"
import { Outlet } from "react-router"
import { Helmet } from "react-helmet-async"
import { useAuth } from "@/contexts/AuthContext"
import { Header } from "./Header"
import { TabBar } from "./TabBar"
import { MetricsTicker } from "./MetricsTicker"
import { Footer } from "./Footer"
import { ChatFAB } from "../chat/ChatFAB"
import { ChatDrawer } from "../chat/ChatDrawer"

class ShellErrorBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state: { error: Error | null } = { error: null }

  static getDerivedStateFromError(error: Error) {
    return { error }
  }

  render() {
    if (this.state.error) {
      return (
        <main className="mx-auto max-w-7xl px-4 py-16">
          <h1 className="text-lg font-semibold mb-2">This briefing failed to render</h1>
          <p className="text-sm text-muted-foreground">{this.state.error.message}</p>
        </main>
      )
    }
    return this.props.children
  }
}

export function AppShell() {
  const [chatOpen, setChatOpen] = useState(false)
  const { user } = useAuth()
  const isDevSession = user?.email === "dev@localhost"

  return (
    <div
      className="app-atmosphere flex flex-col min-h-screen text-foreground"
      style={{ minHeight: "100vh", backgroundColor: "#f4f0e8", color: "#141311" }}
    >
      <Helmet>
        <meta name="robots" content="noindex, nofollow" />
        <meta name="theme-color" content="#F4F0E8" />
      </Helmet>
      {isDevSession && (
        <p className="bg-amber-100 text-amber-950 text-xs text-center py-1.5 px-3">
          Dev session — Google sign-in is bypassed locally.
        </p>
      )}
      <ShellErrorBoundary>
        <Header />
      </ShellErrorBoundary>
      <ShellErrorBoundary>
        <MetricsTicker />
      </ShellErrorBoundary>
      <ShellErrorBoundary>
        <TabBar />
      </ShellErrorBoundary>
      <main className="mx-auto max-w-7xl px-4 py-6 w-full flex-1">
        <ShellErrorBoundary>
          <Outlet />
        </ShellErrorBoundary>
      </main>
      <Footer />
      <ChatFAB onClick={() => setChatOpen(true)} />
      <ChatDrawer open={chatOpen} onClose={() => setChatOpen(false)} />
    </div>
  )
}
