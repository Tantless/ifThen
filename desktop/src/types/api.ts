export type ConversationRead = {
  id: number
  title: string
  chat_type: string
  self_display_name: string
  other_display_name: string
  source_format: string
  status: string
}

export type JobRead = {
  id: number
  status: string
  current_stage: string
  progress_percent: number
  current_stage_percent: number
  current_stage_total_units: number
  current_stage_completed_units: number
  overall_total_units: number
  overall_completed_units: number
  status_message: string | null
}

export type MessageRead = {
  id: number
  sequence_no: number
  speaker_name: string
  speaker_role: string
  timestamp: string
  content_text: string
  message_type: string
  resource_items: Record<string, unknown>[] | null
}

export type MessageDayRead = {
  date: string
  message_count: number
}

export type TopicRead = {
  id: number
  topic_name: string
  topic_summary: string
  topic_status: string
}

export type PersonaProfileRead = {
  subject_role: string
  global_persona_summary: string
  style_traits: string[]
  conflict_traits: string[]
  relationship_specific_patterns: string[]
  confidence: number
}

export type SnapshotRead = {
  id: number
  as_of_message_id: number
  as_of_time: string
  relationship_temperature: string
  tension_level: string
  openness_level: string
  initiative_balance: string
  defensiveness_level: string
  unresolved_conflict_flags: string[]
  relationship_phase: string
  snapshot_summary: string
}

export type SettingRead = {
  setting_key: string
  setting_value: string
  is_secret: boolean
}

export type SettingWrite = {
  setting_key: string
  setting_value: string
  is_secret: boolean
}

export type ListMessagesInput = {
  conversationId: number
  limit?: number
  before?: number
  after?: number
  keyword?: string
  date?: string
  order?: 'asc' | 'desc'
}

export type ReadSnapshotInput = {
  conversationId: number
  at?: string
}

export type ImportConversationRequest = {
  selfDisplayName: string
  autoAnalyze?: boolean
}

export type ListConversationJobsInput = {
  conversationId: number
  limit?: number
}

export type ListConversationSimulationJobsInput = {
  conversationId: number
  limit?: number
}

export type ImportResponse = {
  conversation: ConversationRead
  job: JobRead
}

export type SimulationCreate = {
  conversation_id: number
  target_message_id: number
  replacement_content: string
  mode: 'single_reply' | 'short_thread'
  turn_count: number
}

export type SimulationJobRead = {
  id: number
  conversation_id: number
  target_message_id: number
  mode: string
  turn_count: number
  replacement_content: string
  status: string
  current_stage: string
  progress_percent: number
  current_stage_percent: number
  current_stage_total_units: number
  current_stage_completed_units: number
  overall_total_units: number
  overall_completed_units: number
  status_message: string | null
  result_simulation_id: number | null
  error_message: string | null
}

export type SimulationTurnRead = {
  turn_index: number
  speaker_role: string
  message_text: string
  strategy_used: string
  state_after_turn: Record<string, unknown>
  generation_notes: string | null
}

export type SimulationRead = {
  id: number
  mode: string
  replacement_content: string
  first_reply_text: string | null
  impact_summary: string | null
  simulated_turns: SimulationTurnRead[]
}
