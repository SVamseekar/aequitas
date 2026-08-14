import { lazy, Suspense } from "react"
import { BrowserRouter, Navigate, Routes, Route, useLocation } from "react-router"
import { HelmetProvider } from "react-helmet-async"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { AuthProvider } from "@/contexts/AuthContext"
import { ProtectedRoute } from "@/components/auth/ProtectedRoute"
import { AppShell } from "./components/layout/AppShell"
import { HomePage } from "./components/home/HomePage"
import { DimensionPage } from "./components/dimension/DimensionPage"
import { GoogleAnalytics } from "@/components/GoogleAnalytics"
import { appPath, legacyDashboardToApp, productSlugOrNull, withSearch } from "@/lib/appRoutes"

const AuthPage = lazy(() => import("./pages/AuthPage"))
const ProfilePage = lazy(() => import("./pages/ProfilePage"))
const LandingPage = lazy(() => import("./pages/LandingPage"))
const AboutPage = lazy(() => import("./pages/AboutPage"))
const DisclaimerPage = lazy(() => import("./pages/DisclaimerPage"))
const ContactPage = lazy(() => import("./pages/ContactPage"))
const PrivacyPage = lazy(() => import("./pages/PrivacyPage"))
const TermsPage = lazy(() => import("./pages/TermsPage"))
const MethodologyPage = lazy(() => import("./pages/MethodologyPage"))
const AccessibilityPage = lazy(() => import("./pages/AccessibilityPage"))
const ComparePage = lazy(() => import("./pages/ComparePage"))
const StudioPage = lazy(() => import("./pages/StudioPage"))
const ReachPage = lazy(() => import("./pages/ReachPage"))
const TimePage = lazy(() => import("./pages/TimePage"))
const InviteAcceptPage = lazy(() => import("./pages/InviteAcceptPage"))

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
      <div className="min-h-screen app-atmosphere">
        <div className="max-w-3xl mx-auto px-6 py-10">
          <h1 className="text-xl font-semibold tracking-tight text-foreground mb-6">{title}</h1>
          <Component />
        </div>
      </div>
    )
  }
}

const queryClient = new QueryClient()
const fallback = (
  <div className="min-h-screen flex items-center justify-center">
    <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
  </div>
)

function LegacyDashboardRedirect() {
  const location = useLocation()
  return <Navigate to={legacyDashboardToApp(location.pathname, location.search)} replace />
}

function WarehouseSlugRedirect() {
  const location = useLocation()
  const parts = location.pathname.split("/").filter(Boolean)
  const country = parts[1] ?? "england"
  const slug = parts[2] ?? ""
  const product = productSlugOrNull(slug)
  if (product && product !== slug) {
    const next = withSearch(appPath(country, product), location.search)
    return <Navigate to={`${next.pathname}${next.search}`} replace />
  }
  return <DimensionPage />
}

export default function App() {
  return (
    <HelmetProvider>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Suspense fallback={fallback}>
            <Routes>
              {/* Public */}
              <Route index element={<LandingPage />} />
              <Route path="/about" element={<AboutPage />} />
              <Route path="/disclaimer" element={<DisclaimerPage />} />
              <Route path="/contact" element={<ContactPage />} />
              <Route path="/privacy" element={<PrivacyPage />} />
              <Route path="/terms" element={<TermsPage />} />
              <Route path="/refunds" element={<Navigate to="/about" replace />} />
              <Route path="/methodology" element={<MethodologyPage />} />
              <Route path="/accessibility" element={<AccessibilityPage />} />
              <Route path="/auth" element={<AuthPage />} />
              <Route path="/invite/:token" element={<InviteAcceptPage />} />

              <Route path="/dashboard/*" element={<LegacyDashboardRedirect />} />
              <Route path="/dashboard" element={<LegacyDashboardRedirect />} />

              {/* Pathless layout + absolute children — matches reliably on react-router 8 */}
              <Route element={<AppShell />}>
                <Route path="/app/:country" element={<HomePage />} />
                <Route path="/app/:country/compare" element={<ComparePage />} />
                <Route path="/app/:country/studio" element={<StudioPage />} />
                <Route path="/app/:country/reach" element={<ReachPage />} />
                <Route path="/app/:country/time" element={<TimePage />} />
                <Route path="/app/:country/:dimensionSlug" element={<WarehouseSlugRedirect />} />
              </Route>

              {/* Protected — personal / tenant data */}
              <Route path="/profile" element={<ProtectedRoute><ProfilePage /></ProtectedRoute>} />
              <Route path="/saved" element={<ProtectedRoute><SavedPage /></ProtectedRoute>} />
              <Route path="/notes" element={<ProtectedRoute><NotesPage /></ProtectedRoute>} />
              <Route path="/regions" element={<ProtectedRoute><RegionsPage /></ProtectedRoute>} />
              <Route
                path="*"
                element={
                  <main className="min-h-screen p-8 text-foreground bg-background">
                    <h1 className="text-xl font-semibold mb-2">Page not found</h1>
                    <a className="text-primary underline" href="/app/england">
                      Open the England briefing
                    </a>
                  </main>
                }
              />
            </Routes>
          </Suspense>
        </BrowserRouter>
      </AuthProvider>
      <GoogleAnalytics />
    </QueryClientProvider>
    </HelmetProvider>
  )
}
