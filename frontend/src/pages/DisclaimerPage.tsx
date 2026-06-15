import { useNavigate } from "react-router"
import { ArrowLeft } from "lucide-react"
import { Seo } from "@/components/shared/Seo"

export default function DisclaimerPage() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-background">
      <Seo
        title="Disclaimer — Aequitas"
        description="Aequitas is a policy analysis tool, not official government guidance. Read about data limitations and intended use."
        path="/disclaimer"
      />
      <div className="border-b border-border bg-card/50">
        <div className="max-w-4xl mx-auto px-4 flex items-center h-8">
          <span className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest">Disclaimer</span>
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
        <span className="text-[11px] font-mono uppercase tracking-[0.2em] text-indigo-400 font-medium">Legal Disclaimer</span>
        <h1 className="text-2xl font-bold tracking-tight mt-3 mb-4 text-foreground">
          Not Official Government Guidance
        </h1>
        <p className="text-sm text-muted-foreground leading-relaxed mb-10 max-w-2xl">
          Aequitas is an independent policy intelligence tool. It is not affiliated with, endorsed by,
          or produced by the Department for Transport (DfT), the Office for National Statistics (ONS),
          or any other UK government body.
        </p>

        <div className="space-y-6">
          {[
            {
              title: "Data Accuracy",
              body: "All analytics are derived from publicly available government datasets (NaPTAN, BODS GTFS, ONS Census 2021, MHCLG IMD 2025, NOMIS BRES 2023, NHS ODS, GIAS, DfT TAG v2.03fc, DESNZ 2025). While every effort has been made to process these datasets accurately, Aequitas makes no warranty as to the completeness, accuracy, or fitness for purpose of the analytics presented.",
            },
            {
              title: "Not Official DfT Guidance",
              body: "The economic appraisal figures (BCR, NPV, GDP multipliers) use TAG v2.03fc methodology but have not been validated by DfT. They are indicative estimates for policy exploration, not formal scheme appraisal outputs. Any investment decisions should use DfT-accredited appraisal processes.",
            },
            {
              title: "AI-Generated Content",
              body: "The chatbot uses Gemini Flash grounded in pre-computed narratives. Responses may contain errors, omissions, or misinterpretations. All AI responses should be independently verified against primary data sources before use in policy documents.",
            },
            {
              title: "Temporal Limitations",
              body: "Data reflects the point-in-time snapshots of each source dataset: BODS GTFS (2024–25 timetables), ONS Census 2021, IMD 2025, BRES 2023. Bus network conditions, operator patterns, and deprivation indices change over time. Do not treat outputs as current operational data.",
            },
            {
              title: "Liability",
              body: "The authors accept no liability for decisions made on the basis of Aequitas outputs. Users assume full responsibility for how analytics are interpreted and applied.",
            },
            {
              title: "Open Data Licences",
              body: "Underlying datasets are licensed under the Open Government Licence v3.0 (OGL3), the Open Data Commons Open Database Licence (ODbL), and other open licences as specified by each originating body. Aequitas does not redistribute raw source data.",
            },
          ].map((s) => (
            <div key={s.title} className="border border-border rounded bg-card p-4">
              <p className="text-xs font-semibold text-indigo-400 mb-2">{s.title}</p>
              <p className="text-xs text-muted-foreground leading-relaxed">{s.body}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
