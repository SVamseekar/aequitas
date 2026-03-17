import { lazy, Suspense } from "react"
import { BrowserRouter, Routes, Route } from "react-router"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { AuthProvider } from "@/contexts/AuthContext"
import { ProtectedRoute } from "@/components/auth/ProtectedRoute"
import { AppShell } from "./components/layout/AppShell"
import { HomePage } from "./components/home/HomePage"
import { DimensionPage } from "./components/dimension/DimensionPage"

const AuthPage = lazy(() => import("./pages/AuthPage"))
const ProfilePage = lazy(() => import("./pages/ProfilePage"))
const LandingPage = lazy(() => import("./pages/LandingPage"))
const AboutPage = lazy(() => import("./pages/AboutPage"))
const DisclaimerPage = lazy(() => import("./pages/DisclaimerPage"))
const ContactPage = lazy(() => import("./pages/ContactPage"))
const ComparePage = lazy(() => import("./pages/ComparePage"))

// Saved sub-pages rendered inside a simple wrapper
const SavedPage = lazy(() =>
  import("./components/saved/SavedAnalyses").then((m) => ({ default: SavedPageWrapper(m.SavedAnalyses, "Saved Analyses") }))
)
const NotesPage = lazy(() =>
  import("./components/saved/PolicyNotes").then((m) => ({ default: SavedPageWrapper(m.PolicyNotes, "Policy Notes") }))
)
const RegionsPage = lazy(() =>
  import("./components/saved/SavedRegions").then((m) => ({ default: SavedPageWrapper(m.SavedRegions, "Saved Regions") }))
)

function SavedPageWrapper(Component: React.ComponentType, title: string) {
  return function WrappedPage() {
    return (
      <div className="min-h-screen bg-background">
        <div className="max-w-3xl mx-auto px-6 py-10">
          <h1 className="text-base font-bold tracking-tight text-foreground mb-6">{title}</h1>
          <Component />
        </div>
      </div>
    )
  }
}

const queryClient = new QueryClient()
const fallback = <div className="min-h-screen flex items-center justify-center"><div className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" /></div>

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Suspense fallback={fallback}>
            <Routes>
              {/* Public — marketing + info pages */}
              <Route path="/landing" element={<LandingPage />} />
              <Route path="/about" element={<AboutPage />} />
              <Route path="/disclaimer" element={<DisclaimerPage />} />
              <Route path="/contact" element={<ContactPage />} />
              <Route path="/auth" element={<AuthPage />} />

              {/* Protected — main app shell */}
              <Route element={<ProtectedRoute><AppShell /></ProtectedRoute>}>
                <Route index element={<HomePage />} />
                <Route path=":dimensionSlug" element={<DimensionPage />} />
              </Route>

              {/* Protected — compare page (standalone, no AppShell) */}
              <Route path="/compare" element={<ProtectedRoute><ComparePage /></ProtectedRoute>} />

              {/* Protected — standalone pages */}
              <Route path="/profile" element={<ProtectedRoute><ProfilePage /></ProtectedRoute>} />
              <Route path="/saved" element={<ProtectedRoute><SavedPage /></ProtectedRoute>} />
              <Route path="/notes" element={<ProtectedRoute><NotesPage /></ProtectedRoute>} />
              <Route path="/regions" element={<ProtectedRoute><RegionsPage /></ProtectedRoute>} />
            </Routes>
          </Suspense>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  )
}
