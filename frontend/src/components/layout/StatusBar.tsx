export function StatusBar() {
  const now = new Date()
  const dateStr = now.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" })

  return (
    <div className="border-b border-border bg-card/50 h-8 flex items-center">
      <div className="max-w-7xl mx-auto px-4 w-full flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
          <span className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest">
            Aequitas Intelligence — Systems Online
          </span>
        </div>
        <span className="text-[10px] font-mono text-muted-foreground/40 hidden sm:block">
          {dateStr} · NaPTAN · BODS · ONS · IMD · DfT TAG
        </span>
      </div>
    </div>
  )
}
