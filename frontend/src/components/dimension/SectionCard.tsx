import { useState } from "react"
import type { SectionItem } from "@/api/types"
import { Markdown } from "@/components/shared/Markdown"

interface Props {
  section: SectionItem
}

export function SectionCard({ section }: Props) {
  const [open, setOpen] = useState(false)
  const title = (section.chart_data?.title as string | undefined) ?? section.section_id

  return (
    <article className="bg-white rounded-lg border border-gray-200 p-6 mb-4">
      <h3 className="text-lg font-semibold text-gray-900 mb-2">{title}</h3>

      {/* Chart placeholder — will be replaced by ChartRenderer in Chunk 5 */}
      <div className="bg-gray-100 rounded-md p-8 text-center text-gray-400 text-sm mb-3">
        Chart: {(section.chart_data as Record<string, unknown>)?.type as string ?? "unknown"}
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
