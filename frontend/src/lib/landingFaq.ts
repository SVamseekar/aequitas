export const FAQ_ITEMS = [
  {
    question: "Which countries?",
    answer: "England, Ireland (Republic), the Netherlands, France. Ranks stay in-country.",
  },
  {
    question: "What is the score?",
    answer:
      "0–100 from 400 m coverage, evening service, weekday quality, and inverted deprivation–service correlation. Missing terms drop out.",
  },
  {
    question: "15 / 30 / 45 minute jobs?",
    answer: "Only after a local r5py run. Otherwise Reach shows service bands and an empty travel-time line.",
  },
  {
    question: "Official guidance?",
    answer: "No. Independent briefing. Not DfT, NTA, CBS, or ministerial advice.",
  },
  {
    question: "Live punctuality?",
    answer: "Only the last official GTFS-RT / SIRI rollup. No invented national on-time rate.",
  },
  {
    question: "Can I run it locally?",
    answer: "Yes. Clone the repo and run ./scripts/dev.sh. Warehouses stay on disk, not on this host.",
  },
] as const

