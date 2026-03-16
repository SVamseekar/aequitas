import { BrowserRouter, Routes, Route } from "react-router"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { AppShell } from "./components/layout/AppShell"

const queryClient = new QueryClient()

function Placeholder({ name }: { name: string }) {
  return <div className="text-gray-500">Page: {name}</div>
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<AppShell />}>
            <Route index element={<Placeholder name="Home" />} />
            <Route path=":dimensionSlug" element={<Placeholder name="Dimension" />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
