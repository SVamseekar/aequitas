import { createClient } from "@supabase/supabase-js"

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL as string | undefined
const supabaseKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY as string | undefined

if (!supabaseUrl || !supabaseKey) {
  console.warn("Supabase credentials not configured — auth will be disabled")
}

export const supabase = createClient(
  supabaseUrl ?? "http://localhost:54321",
  supabaseKey ?? "placeholder",
)
