import { useNavigate } from "react-router"
import { useState } from "react"
import { ArrowLeft, GitBranch, Mail, Loader2, CheckCircle2, AlertCircle } from "lucide-react"
import { Seo } from "@/components/shared/Seo"
import { SUPPORT_EMAIL } from "@/lib/site"

type FormStatus = "idle" | "submitting" | "success" | "error"

export default function ContactPage() {
  const navigate = useNavigate()
  const [name, setName] = useState("")
  const [email, setEmail] = useState("")
  const [org, setOrg] = useState("")
  const [message, setMessage] = useState("")
  const [status, setStatus] = useState<FormStatus>("idle")
  const [errorMessage, setErrorMessage] = useState("")
  const [formStartedAt] = useState(() => Date.now())

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setStatus("submitting")
    setErrorMessage("")

    try {
      const response = await fetch("/api/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, organisation: org, message, formStartedAt }),
      })
      const data = (await response.json().catch(() => ({}))) as { error?: string }
      if (!response.ok) {
        throw new Error(data.error ?? "Failed to send message")
      }
      setStatus("success")
    } catch (error) {
      setStatus("error")
      setErrorMessage(error instanceof Error ? error.message : "Something went wrong")
    }
  }

  return (
    <div className="min-h-screen bg-background">
      <Seo
        title="Contact Aequitas — Feedback & Research Enquiries"
        description="Get in touch with the Aequitas team for bug reports, data accuracy issues, research collaboration, or institutional use cases."
        path="/contact"
      />
      <div className="border-b border-border bg-card/50">
        <div className="max-w-4xl mx-auto px-4 flex items-center h-8">
          <span className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest">Contact</span>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-12">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground mb-8 font-mono transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> BACK
        </button>

        <div className="h-px bg-indigo-500/40 mb-8 max-w-xs" />
        <span className="text-[11px] font-mono uppercase tracking-[0.2em] text-indigo-400 font-medium">Contact & Feedback</span>
        <h1 className="text-2xl font-bold tracking-tight mt-3 mb-4 text-foreground">
          Get in Touch
        </h1>
        <p className="text-sm text-muted-foreground leading-relaxed mb-10 max-w-2xl">
          Aequitas is an open research project. Feedback from transport researchers, LTA planners,
          and policy analysts is welcome.
        </p>

        <div className="grid sm:grid-cols-2 gap-4 mb-10">
          <div className="border border-border rounded bg-card p-5">
            <div className="flex items-center gap-2 mb-3">
              <GitBranch className="w-4 h-4 text-indigo-400" />
              <p className="text-xs font-semibold text-foreground">GitHub Issues</p>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed mb-3">
              Bug reports, feature requests, and data accuracy issues. Please include the dimension,
              metric, and LSOA/region in question.
            </p>
            <a
              href="https://github.com/SVamseekar/aequitas/issues"
              target="_blank"
              rel="noopener noreferrer"
              className="text-[11px] font-mono text-indigo-400 uppercase tracking-wide hover:underline"
            >
              Open an issue on GitHub
            </a>
          </div>

          <div className="border border-border rounded bg-card p-5">
            <div className="flex items-center gap-2 mb-3">
              <Mail className="w-4 h-4 text-indigo-400" />
              <p className="text-xs font-semibold text-foreground">Research Enquiries</p>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed mb-3">
              For research collaboration, data licensing questions, or institutional use cases,
              email us directly.
            </p>
            <a
              href={`mailto:${SUPPORT_EMAIL}`}
              className="text-[11px] font-mono text-indigo-400 uppercase tracking-wide hover:underline"
            >
              {SUPPORT_EMAIL}
            </a>
          </div>
        </div>

        <section className="mb-12">
          <h2 className="text-[11px] uppercase tracking-[0.15em] text-muted-foreground font-mono mb-4">
            Send a Message
          </h2>
          {status === "success" ? (
            <div className="border border-emerald-500/30 rounded bg-card p-5 max-w-xl flex items-start gap-3">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />
              <div>
                <p className="text-xs font-semibold text-foreground mb-1">Message sent</p>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  Thanks — we&apos;ll get back to you at <span className="text-foreground">{email}</span> soon.
                </p>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="border border-border rounded bg-card p-5 space-y-4 max-w-xl">
              <div className="grid sm:grid-cols-2 gap-4">
                <label className="block">
                  <span className="text-[11px] font-mono text-muted-foreground uppercase tracking-wide mb-1.5 block">
                    Name <em className="text-indigo-400 not-italic">*</em>
                  </span>
                  <input
                    required
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full text-xs bg-background border border-border rounded px-3 py-2 text-foreground focus:outline-none focus:ring-1 focus:ring-indigo-400"
                  />
                </label>
                <label className="block">
                  <span className="text-[11px] font-mono text-muted-foreground uppercase tracking-wide mb-1.5 block">
                    Email <em className="text-indigo-400 not-italic">*</em>
                  </span>
                  <input
                    required
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full text-xs bg-background border border-border rounded px-3 py-2 text-foreground focus:outline-none focus:ring-1 focus:ring-indigo-400"
                  />
                </label>
              </div>
              <label className="block">
                <span className="text-[11px] font-mono text-muted-foreground uppercase tracking-wide mb-1.5 block">
                  Organisation (optional)
                </span>
                <input
                  type="text"
                  value={org}
                  onChange={(e) => setOrg(e.target.value)}
                  placeholder="e.g. Transport for Greater Manchester"
                  className="w-full text-xs bg-background border border-border rounded px-3 py-2 text-foreground focus:outline-none focus:ring-1 focus:ring-indigo-400"
                />
              </label>
              <label className="block">
                <span className="text-[11px] font-mono text-muted-foreground uppercase tracking-wide mb-1.5 block">
                  Message <em className="text-indigo-400 not-italic">*</em>
                </span>
                <textarea
                  required
                  rows={4}
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  className="w-full text-xs bg-background border border-border rounded px-3 py-2 text-foreground focus:outline-none focus:ring-1 focus:ring-indigo-400"
                />
              </label>

              {status === "error" && (
                <div className="flex items-center gap-2 text-xs text-red-400" role="alert">
                  <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                  <span>{errorMessage}</span>
                </div>
              )}

              <button
                type="submit"
                disabled={status === "submitting"}
                className="flex items-center gap-2 text-[11px] font-mono uppercase tracking-wide bg-indigo-600 hover:bg-indigo-500 disabled:opacity-60 text-white rounded px-4 py-2 transition-colors"
              >
                {status === "submitting" ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" /> Sending…
                  </>
                ) : (
                  "Send message"
                )}
              </button>
            </form>
          )}
        </section>

        <section>
          <h2 className="text-[11px] uppercase tracking-[0.15em] text-muted-foreground font-mono mb-4">
            Known Limitations
          </h2>
          <div className="border border-border rounded bg-card p-4 text-xs text-muted-foreground leading-relaxed space-y-2">
            <p>The 400m Euclidean catchment for accessibility metrics underestimates true walking distances
              in areas with physical barriers (rivers, railways, motorways). Network-distance catchments
              are planned for Phase 3.</p>
            <p>BODS GTFS feeds cover 2024–25 timetables. Rural operators with fewer than 5 vehicles
              may be underrepresented. Demand-responsive transport (DRT) services are not captured.</p>
            <p>Modal shift estimates use DfT aggregate elasticities, not revealed-preference data.
              Local elasticity variation is not modelled.</p>
          </div>
        </section>
      </div>
    </div>
  )
}
