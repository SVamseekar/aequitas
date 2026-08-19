import { useState } from "react"
import { Loader2, AlertCircle } from "lucide-react"
import { Seo } from "@/components/shared/Seo"
import { SUPPORT_EMAIL } from "@/lib/site"
import { BriefingLayout } from "./briefing/BriefingLayout"

type FormStatus = "idle" | "submitting" | "success" | "error"

const inputClass =
  "w-full text-base bg-[var(--l-surface)] border border-[var(--l-rule)] rounded-sm px-3.5 py-2.5 text-[var(--l-ink)] placeholder:text-[var(--l-slate)]/70 focus:outline-none focus:ring-2 focus:ring-[var(--l-rust)]"

const INTERESTS = [
  "A new country pack",
  "Adapt the method to our index",
  "A briefing for one authority",
  "Research or teaching",
  "Something else",
] as const

export default function ContactPage() {
  const [name, setName] = useState("")
  const [email, setEmail] = useState("")
  const [org, setOrg] = useState("")
  const [country, setCountry] = useState("")
  const [interest, setInterest] = useState<(typeof INTERESTS)[number] | "">("")
  const [message, setMessage] = useState("")
  const [status, setStatus] = useState<FormStatus>("idle")
  const [errorMessage, setErrorMessage] = useState("")
  const [formStartedAt] = useState(() => Date.now())

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setStatus("submitting")
    setErrorMessage("")

    const composed = [
      interest && `Interest: ${interest}`,
      country && `Country / region: ${country}`,
      message,
    ]
      .filter(Boolean)
      .join("\n\n")

    try {
      const response = await fetch("/api/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          email,
          organisation: org,
          message: composed,
          formStartedAt,
        }),
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
        title="Work with us — Aequitas"
        description="Commission a country pack. Transport authorities, ministries, operators, and researchers — official timetables joined to official need."
        path="/contact"
      />
      <p className="text-xs font-medium uppercase tracking-wide text-[var(--l-rust)]">
        Work with us
      </p>
      <h1 className="font-display text-3xl sm:text-4xl text-[var(--l-ink)] mt-2 mb-4">
        Schedule a conversation
      </h1>
      <p className="text-[var(--l-slate)] max-w-xl mb-10 text-pretty">
        Tell us the country, the official sources you already publish, and the decision the
        briefing has to support. We tailor the pack. Ranks stay in-country.
      </p>

      <ul className="grid sm:grid-cols-2 gap-x-8 gap-y-4 mb-12 max-w-2xl text-sm">
        <li>
          <p className="font-semibold text-[var(--l-ink)]">A country pack</p>
          <p className="text-[var(--l-slate)] mt-1">
            Your network feed, your small areas, your deprivation index.
          </p>
        </li>
        <li>
          <p className="font-semibold text-[var(--l-ink)]">A method adaptation</p>
          <p className="text-[var(--l-slate)] mt-1">
            Appraisal rule, destinations, real-time rollup, local statute titles.
          </p>
        </li>
        <li>
          <p className="font-semibold text-[var(--l-ink)]">A single-authority briefing</p>
          <p className="text-[var(--l-slate)] mt-1">
            One filter, the same doors, exhibits you can quote.
          </p>
        </li>
        <li>
          <p className="font-semibold text-[var(--l-ink)]">Research</p>
          <p className="text-[var(--l-slate)] mt-1">
            Dated packs and empty cells that stay empty. Email {SUPPORT_EMAIL}.
          </p>
        </li>
      </ul>

      <section>
        <h2 className="text-lg font-semibold text-[var(--l-ink)] mb-5">Contact</h2>
        {status === "success" ? (
          <p className="text-[var(--l-ink)] max-w-xl">
            Received. We will write to {email}.
          </p>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-5 max-w-xl">
            <div className="grid sm:grid-cols-2 gap-4">
              <label className="block">
                <span className="text-sm font-medium text-[var(--l-ink)] mb-1.5 block">Name</span>
                <input required type="text" value={name} onChange={(e) => setName(e.target.value)} className={inputClass} />
              </label>
              <label className="block">
                <span className="text-sm font-medium text-[var(--l-ink)] mb-1.5 block">Email</span>
                <input required type="email" value={email} onChange={(e) => setEmail(e.target.value)} className={inputClass} />
              </label>
            </div>
            <label className="block">
              <span className="text-sm font-medium text-[var(--l-ink)] mb-1.5 block">Organisation</span>
              <input type="text" value={org} onChange={(e) => setOrg(e.target.value)} className={inputClass} />
            </label>
            <label className="block">
              <span className="text-sm font-medium text-[var(--l-ink)] mb-1.5 block">Country or region</span>
              <input type="text" value={country} onChange={(e) => setCountry(e.target.value)} className={inputClass} />
            </label>
            <label className="block">
              <span className="text-sm font-medium text-[var(--l-ink)] mb-1.5 block">I am interested in</span>
              <select
                value={interest}
                onChange={(e) => setInterest(e.target.value as typeof interest)}
                className={inputClass}
              >
                <option value="">Select…</option>
                {INTERESTS.map((i) => (
                  <option key={i} value={i}>
                    {i}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="text-sm font-medium text-[var(--l-ink)] mb-1.5 block">
                Project
              </span>
              <textarea
                required
                rows={5}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="What decision does this briefing have to support?"
                className={inputClass}
              />
            </label>
            <input type="text" name="website" tabIndex={-1} autoComplete="off" className="hidden" aria-hidden />

            {status === "error" && (
              <div className="flex items-center gap-2 text-sm text-red-700" role="alert">
                <AlertCircle className="w-4 h-4 shrink-0" aria-hidden />
                <span>{errorMessage}</span>
              </div>
            )}

            <button type="submit" disabled={status === "submitting"} className="landing-btn-primary disabled:opacity-60">
              {status === "submitting" ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" aria-hidden /> Sending…
                </>
              ) : (
                "Send"
              )}
            </button>
          </form>
        )}
      </section>
    </BriefingLayout>
  )
}
