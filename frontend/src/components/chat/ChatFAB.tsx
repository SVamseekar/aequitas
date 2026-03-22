interface Props {
  onClick: () => void
}

export function ChatFAB({ onClick }: Props) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="fixed bottom-6 right-6 rounded-full w-14 h-14 bg-indigo-600 hover:bg-indigo-700 text-white shadow-lg z-40 flex items-center justify-center transition-colors"
      aria-label="Open AI chat"
    >
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
      </svg>
    </button>
  )
}
