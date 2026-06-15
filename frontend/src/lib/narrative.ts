const MAX_HEADLINE_LENGTH = 160

/**
 * Extracts a short, scannable headline from a narrative's first section body
 * (text after the first `## ` heading, up to the next heading or paragraph break).
 * Strips markdown emphasis so it renders as plain text in a highlight strip.
 */
export function extractHeadline(narrative: string): string | null {
  const afterHeading = narrative.split(/^##\s+.+$/m)[1]?.trim()
  if (!afterHeading) return null

  const body = afterHeading.split(/\n\s*\n|^##\s+/m)[0]
    .replace(/\*\*/g, "")
    .replace(/[\r\n]+/g, " ")
    .trim()

  if (!body) return null

  if (body.length <= MAX_HEADLINE_LENGTH) return body

  const truncated = body.slice(0, MAX_HEADLINE_LENGTH)
  const lastSentenceEnd = Math.max(truncated.lastIndexOf(". "), truncated.lastIndexOf(") "))
  if (lastSentenceEnd > MAX_HEADLINE_LENGTH * 0.5) {
    return truncated.slice(0, lastSentenceEnd + 1)
  }
  const lastSpace = truncated.lastIndexOf(" ")
  return `${truncated.slice(0, lastSpace > 0 ? lastSpace : MAX_HEADLINE_LENGTH).trim()}…`
}
