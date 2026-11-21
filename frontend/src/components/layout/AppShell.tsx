import { Component, useState, type ReactNode } from "react"
import { Outlet } from "react-router"
import { Helmet } from "react-helmet-async"
import { useAuth } from "@/contexts/AuthContext"
import { Header } from "./Header"
import { TabBar } from "./TabBar"
import {SourceFooter} from './SourceFooter'
import { ChatFAB } from "../chat/ChatFAB"
import { ChatDrawer } from "../chat/ChatDrawer"
import { AssistantContext } from '@/lib/assistantContext'
import {useFilters} from '@/api/hooks'

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
  const { user, activeTenant } = useAuth()
  const {country,region,urbanRural,pack,mode}=useFilters()
  const isDevSession = user?.email === "dev@localhost"

  return (
    <AssistantContext.Provider value={() => setChatOpen(true)}>
    <div
      className="app-redesign min-h-screen text-foreground"
    >
      <Helmet>
        <meta name="robots" content="noindex, nofollow" />
        <meta name="theme-color" content="#F4F0E8" />
      </Helmet>
      <TabBar />
      <div className='app-workspace'>
      {isDevSession && (
        <p className="bg-amber-100 text-amber-950 text-xs text-center py-1.5 px-3">
          Dev session — Google sign-in is bypassed locally.
        </p>
      )}
      <ShellErrorBoundary>
        <Header />
      </ShellErrorBoundary>
      <a href='#main-content' className='app-skip-link'>Skip to content</a>
      <main id='main-content' className="app-content">
        <ShellErrorBoundary>
          <Outlet />
        </ShellErrorBoundary>
      </main>
      <SourceFooter />
      <ChatFAB onClick={() => setChatOpen(true)} />
      <ChatDrawer key={`${user?.id??'anonymous'}:${activeTenant?.id??'none'}:${country}:${region}:${urbanRural}:${pack}:${mode}`} open={chatOpen} onClose={() => setChatOpen(false)} />
      </div>
    </div>
    </AssistantContext.Provider>
  )
}
