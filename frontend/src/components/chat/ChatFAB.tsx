interface Props {
  onClick: () => void
}

export function ChatFAB({ onClick }: Props) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="app-btn-primary fixed bottom-6 right-6 rounded-full w-14 h-14 z-40 flex items-center justify-center shadow-[0_12px_32px_rgb(184_78_31_/_0.35)]"
      aria-label="Open AI chat"
    >
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
      </svg>
    </button>
  )
}
