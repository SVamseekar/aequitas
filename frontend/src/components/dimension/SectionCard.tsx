import { useState } from "react"
import type { SectionItem } from "@/api/types"
import { Markdown } from "@/components/shared/Markdown"
import { ChartRenderer } from "@/components/charts/ChartRenderer"

interface Props {
  section: SectionItem
}

export function SectionCard({ section }: Props) {
  const [open, setOpen] = useState(false)
  const title = (section.chart_data?.title as string | undefined) ?? section.section_id

  return (
    <article className="bg-white rounded-lg border border-gray-200 p-6 mb-4">
      <h3 className="text-lg font-semibold text-gray-900 mb-2">{title}</h3>

      <div className="mb-3">
        <ChartRenderer chartData={section.chart_data} />
      </div>

      <button
        type="button"
        className="text-indigo-600 text-sm font-medium"
        onClick={() => setOpen(!open)}
      >
        {open ? "Hide details" : "Read more"}
      </button>
      {open && (
        <div className="mt-3">
          <Markdown content={section.narrative} />
        </div>
      )}
    </article>
  )
}
