import { supabase } from "@/integrations/supabase/client"

export interface ConversationRow {
  id: string
  user_id: string
  title: string
  created_at: string
  updated_at: string
}

export interface MessageRow {
  id: string
  conversation_id: string
  user_id: string
  role: "user" | "assistant"
  content: string
  created_at: string
}

export interface SavedAnalysisRow {
  id: string
  user_id: string
  title: string
  content: string
  section_id: string | null
  dimension: string | null
  tags: string[]
  created_at: string
}

export interface PolicyNoteRow {
  id: string
  user_id: string
  dimension: string
  region: string
  stance: "priority" | "monitor" | "adequate"
  thesis: string
  critique: string | null
  created_at: string
  updated_at: string
}

export interface SavedRegionRow {
  id: string
  user_id: string
  region_code: string
  region_name: string
  notes: string | null
  created_at: string
}

// --- Conversations ---

export async function createConversation(userId: string, title: string): Promise<string | null> {
  const { data, error } = await supabase
    .from("conversations")
    .insert({ user_id: userId, title })
    .select("id")
    .single()
  if (error) { console.error("createConversation:", error); return null }
  return data.id as string
}

export async function updateConversationTitle(id: string, title: string) {
  await supabase
    .from("conversations")
    .update({ title, updated_at: new Date().toISOString() })
    .eq("id", id)
}

export async function deleteConversation(id: string) {
  await supabase.from("conversations").delete().eq("id", id)
}

export async function listConversations(userId: string): Promise<ConversationRow[]> {
  const { data, error } = await supabase
    .from("conversations")
    .select("*")
    .eq("user_id", userId)
    .order("updated_at", { ascending: false })
    .limit(50)
  if (error) { console.error("listConversations:", error); return [] }
  return (data as ConversationRow[]) ?? []
}

export async function loadMessages(conversationId: string): Promise<MessageRow[]> {
  const { data, error } = await supabase
    .from("messages")
    .select("*")
    .eq("conversation_id", conversationId)
    .order("created_at", { ascending: true })
  if (error) { console.error("loadMessages:", error); return [] }
  return (data as MessageRow[]) ?? []
}

export async function saveMessage(
  conversationId: string,
  userId: string,
  role: "user" | "assistant",
  content: string,
): Promise<string | null> {
  const { data, error } = await supabase
    .from("messages")
    .insert({ conversation_id: conversationId, user_id: userId, role, content })
    .select("id")
    .single()
  if (error) { console.error("saveMessage:", error); return null }
  await supabase
    .from("conversations")
    .update({ updated_at: new Date().toISOString() })
    .eq("id", conversationId)
  return data.id as string
}

// --- Saved Analyses ---

export async function saveAnalysis(
  userId: string,
  title: string,
  content: string,
  sectionId?: string,
  dimension?: string,
  tags: string[] = [],
) {
  const { error } = await supabase
    .from("saved_analyses")
    .insert({ user_id: userId, title, content, section_id: sectionId, dimension, tags })
  if (error) { console.error("saveAnalysis:", error); return false }
  return true
}

export async function listSavedAnalyses(userId: string): Promise<SavedAnalysisRow[]> {
  const { data, error } = await supabase
    .from("saved_analyses")
    .select("*")
    .eq("user_id", userId)
    .order("created_at", { ascending: false })
  if (error) { console.error("listSavedAnalyses:", error); return [] }
  return (data as SavedAnalysisRow[]) ?? []
}

export async function deleteSavedAnalysis(id: string) {
  await supabase.from("saved_analyses").delete().eq("id", id)
}

// --- Policy Notes ---

export async function listPolicyNotes(userId: string): Promise<PolicyNoteRow[]> {
  const { data, error } = await supabase
    .from("policy_notes")
    .select("*")
    .eq("user_id", userId)
    .order("created_at", { ascending: false })
  if (error) { console.error("listPolicyNotes:", error); return [] }
  return (data as PolicyNoteRow[]) ?? []
}

export async function createPolicyNote(
  userId: string,
  note: { dimension: string; region?: string; stance: string; thesis: string },
): Promise<string | null> {
  const { data, error } = await supabase
    .from("policy_notes")
    .insert({ user_id: userId, ...note })
    .select("id")
    .single()
  if (error) { console.error("createPolicyNote:", error); return null }
  return data.id as string
}

export async function deletePolicyNote(id: string) {
  await supabase.from("policy_notes").delete().eq("id", id)
}

// --- Saved Regions ---

export async function listSavedRegions(userId: string): Promise<SavedRegionRow[]> {
  const { data, error } = await supabase
    .from("saved_regions")
    .select("*")
    .eq("user_id", userId)
    .order("created_at", { ascending: false })
  if (error) { console.error("listSavedRegions:", error); return [] }
  return (data as SavedRegionRow[]) ?? []
}

export async function addSavedRegion(
  userId: string,
  region: { region_code: string; region_name: string; notes?: string },
) {
  const { error } = await supabase.from("saved_regions").insert({ user_id: userId, ...region })
  if (error) { console.error("addSavedRegion:", error); return false }
  return true
}

export async function deleteSavedRegion(id: string) {
  await supabase.from("saved_regions").delete().eq("id", id)
}
