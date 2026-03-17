import { useState } from "react"
import { Outlet } from "react-router"
import { Header } from "./Header"
import { TabBar } from "./TabBar"
import { StatusBar } from "./StatusBar"
import { MetricsTicker } from "./MetricsTicker"
import { Footer } from "./Footer"
import { ChatFAB } from "../chat/ChatFAB"
import { ChatDrawer } from "../chat/ChatDrawer"

export function AppShell() {
  const [chatOpen, setChatOpen] = useState(false)

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <StatusBar />
      <Header />
      <MetricsTicker />
      <TabBar />
      <main className="mx-auto max-w-7xl px-4 py-6 w-full flex-1">
        <Outlet />
      </main>
      <Footer />
      <ChatFAB onClick={() => setChatOpen(true)} />
      <ChatDrawer open={chatOpen} onClose={() => setChatOpen(false)} />
    </div>
  )
}
