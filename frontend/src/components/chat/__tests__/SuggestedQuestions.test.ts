import { describe, expect, it } from "vitest"
import { ENGLAND_QUICK_ACTIONS } from "../QuickActions"
import { IRELAND_SUGGESTIONS } from "../SuggestedQuestions"

describe("Ireland chat suggestions", () => {
  it("does not suggest BSA or IMD", () => {
    const blob = IRELAND_SUGGESTIONS.join(" ")
    expect(blob).not.toMatch(/\bBSA\b/)
    expect(blob).not.toMatch(/\bIMD\b/)
    expect(blob).not.toMatch(/Bus Services Act/)
    expect(blob).toMatch(/TFI|Pobal HP|Dublin/)
  })

  it("England Quick Actions stay England-only; Ireland hides them", () => {
    const blob = ENGLAND_QUICK_ACTIONS.map((a) => `${a.label} ${a.prompt}`).join(" ")
    expect(blob).toMatch(/English regions|inequity|Policy/i)
    expect(IRELAND_SUGGESTIONS.join(" ")).not.toMatch(/Explore Inequality|Explore Inequity/)
  })
})

