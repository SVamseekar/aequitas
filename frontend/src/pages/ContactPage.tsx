import { useState } from "react"
import { GitBranch, Mail, Loader2, CheckCircle2, AlertCircle } from "lucide-react"
import { Seo } from "@/components/shared/Seo"
import { SUPPORT_EMAIL } from "@/lib/site"
import { BriefingLayout } from "./briefing/BriefingLayout"

type FormStatus = "idle" | "submitting" | "success" | "error"

const inputClass =
  "w-full text-base app-glass border border-white/60 rounded-xl px-3.5 py-2.5 text-foreground placeholder:text-muted-foreground/70 focus:outline-none focus:ring-2 focus:ring-primary"

export default function ContactPage() {
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
    <BriefingLayout>
      <Seo
        title="Contact Aequitas — Feedback & Research Enquiries"
        description="Get in touch for briefings, data issues, or research."
        path="/contact"
      />
      <p className="text-xs font-medium uppercase tracking-wide text-[var(--l-rust)]">Contact</p>
      <h1 className="font-display text-3xl sm:text-4xl text-[var(--l-ink)] mt-2 mb-4">
        Get in touch
      </h1>
      <p className="text-[var(--l-slate)] max-w-xl mb-10 text-pretty">
        Briefings, data issues, or research. A form — not an essay.
      </p>

        <div className="grid sm:grid-cols-2 gap-4 mb-12">
          <div className="app-glass-strong rounded-2xl border border-white/60 p-5">
            <div className="flex items-center gap-2 mb-3">
              <GitBranch className="w-4 h-4 text-primary" aria-hidden />
              <p className="text-base font-semibold text-foreground">GitHub Issues</p>
            </div>
            <p className="text-base text-muted-foreground leading-relaxed mb-3">
              Bug reports, feature requests, and data accuracy issues. Please include the dimension,
              metric, and LSOA/region in question.
            </p>
            <a
              href="https://github.com/SVamseekar/aequitas/issues"
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm font-medium text-primary hover:underline"
            >
              Open an issue on GitHub
            </a>
          </div>

          <div className="app-glass-strong rounded-2xl border border-white/60 p-5">
            <div className="flex items-center gap-2 mb-3">
              <Mail className="w-4 h-4 text-primary" aria-hidden />
              <p className="text-base font-semibold text-foreground">Research Enquiries</p>
            </div>
            <p className="text-base text-muted-foreground leading-relaxed mb-3">
              For research collaboration, data licensing questions, or institutional use cases,
              email us directly.
            </p>
            <a
              href={`mailto:${SUPPORT_EMAIL}`}
              className="text-sm font-medium text-primary hover:underline break-all"
            >
              {SUPPORT_EMAIL}
            </a>
          </div>
        </div>

        <section className="mb-12">
          <h2 className="text-lg font-semibold text-foreground mb-5">Send a Message</h2>
          {status === "success" ? (
            <div className="app-glass-strong border border-emerald-500/30 rounded-2xl p-5 max-w-xl flex items-start gap-3">
              <CheckCircle2 className="w-5 h-5 text-emerald-400 mt-0.5 shrink-0" aria-hidden />
              <div>
                <p className="text-base font-semibold text-foreground mb-1">Message sent</p>
                <p className="text-base text-muted-foreground leading-relaxed">
                  Thanks — we&apos;ll get back to you at{" "}
                  <span className="text-foreground">{email}</span> soon.
                </p>
              </div>
            </div>
          ) : (
            <form
              onSubmit={handleSubmit}
              className="app-glass-strong rounded-2xl border border-white/60 p-5 sm:p-6 space-y-5 max-w-xl"
            >
              <div className="grid sm:grid-cols-2 gap-4">
                <label className="block">
                  <span className="text-sm font-medium text-foreground mb-1.5 block">
                    Name <span className="text-primary">*</span>
                  </span>
                  <input
                    required
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className={inputClass}
                  />
                </label>
                <label className="block">
                  <span className="text-sm font-medium text-foreground mb-1.5 block">
                    Email <span className="text-primary">*</span>
                  </span>
                  <input
                    required
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className={inputClass}
                  />
                </label>
              </div>
              <label className="block">
                <span className="text-sm font-medium text-foreground mb-1.5 block">
                  Organisation (optional)
                </span>
                <input
                  type="text"
                  value={org}
                  onChange={(e) => setOrg(e.target.value)}
                  placeholder="e.g. Transport for Greater Manchester"
                  className={inputClass}
                />
              </label>
              <label className="block">
                <span className="text-sm font-medium text-foreground mb-1.5 block">
                  Message <span className="text-primary">*</span>
                </span>
                <textarea
                  required
                  rows={5}
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  className={inputClass}
                />
              </label>

              {status === "error" && (
                <div className="flex items-center gap-2 text-sm text-red-400" role="alert">
                  <AlertCircle className="w-4 h-4 shrink-0" aria-hidden />
                  <span>{errorMessage}</span>
                </div>
              )}

              <button
                type="submit"
                disabled={status === "submitting"}
                className="landing-btn-primary disabled:opacity-60"
              >
                {status === "submitting" ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" aria-hidden /> Sending…
                  </>
                ) : (
                  "Send message"
                )}
              </button>
            </form>
          )}
        </section>

    </BriefingLayout>
  )
}
