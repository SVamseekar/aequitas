import { useState } from "react"
import { Outlet } from "react-router"
import { Header } from "./Header"
import { TabBar } from "./TabBar"
import { ChatFAB } from "../chat/ChatFAB"
import { ChatDrawer } from "../chat/ChatDrawer"

export function AppShell() {
  const [chatOpen, setChatOpen] = useState(false)

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <TabBar />
      <main className="mx-auto max-w-7xl px-4 py-6">
        <Outlet />
      </main>
      <ChatFAB onClick={() => setChatOpen(true)} />
      <ChatDrawer open={chatOpen} onClose={() => setChatOpen(false)} />
    </div>
  )
}
