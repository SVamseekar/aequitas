import { createContext } from 'react'

export const AssistantContext = createContext<(() => void) | null>(null)
