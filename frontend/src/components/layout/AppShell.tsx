import { Outlet } from "react-router"
import { Header } from "./Header"
import { TabBar } from "./TabBar"

export function AppShell() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <TabBar />
      <main className="mx-auto max-w-7xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}
