import type {
  ConversationRead,
  ImportConversationRequest,
  ImportResponse,
  JobRead,
  ListConversationJobsInput,
  ListConversationSimulationJobsInput,
  ListMessagesInput,
  MessageContextRead,
  MessageDayRead,
  MessageRead,
  PersonaProfileRead,
  ReadMessageContextInput,
  ReadSnapshotInput,
  SettingRead,
  SettingWrite,
  SimulationCreate,
  SimulationJobRead,
  SimulationRead,
  SnapshotRead,
  TopicRead,
} from './api.js'

export type DesktopServiceState = {
  phase: 'booting' | 'starting-api' | 'starting-worker' | 'waiting-api' | 'ready' | 'error'
  detail?: string
}

export type DesktopFileSelectionPayload = {
  canceled: boolean
  filePaths: string[]
}

export type DesktopAppInfo = {
  name: string
  version: string
}

export type DesktopAvatarFilePayload = {
  fileName: string
  mimeType: string
  dataUrl: string
}

export type DesktopWindowState = {
  isMaximized: boolean
}

export type DesktopWindowBridge = {
  minimize: () => Promise<void>
  toggleMaximize: () => Promise<DesktopWindowState>
  close: () => Promise<void>
  getState: () => Promise<DesktopWindowState>
}

export type DesktopSettingsBridge = {
  read: () => Promise<SettingRead[]>
  write: (payload: SettingWrite) => Promise<SettingRead>
}

export type DesktopConversationsBridge = {
  list: () => Promise<ConversationRead[]>
  delete: (conversationId: number) => Promise<void>
  listMessages: (payload: ListMessagesInput) => Promise<MessageRead[]>
  listMessageDays: (conversationId: number) => Promise<MessageDayRead[]>
  readMessageContext: (payload: ReadMessageContextInput) => Promise<MessageContextRead>
  listTopics: (conversationId: number) => Promise<TopicRead[]>
  readProfile: (conversationId: number) => Promise<PersonaProfileRead[]>
  readSnapshot: (payload: ReadSnapshotInput) => Promise<SnapshotRead>
  import: (payload: ImportConversationRequest) => Promise<ImportResponse>
  startAnalysis: (conversationId: number) => Promise<JobRead>
}

export type DesktopJobsBridge = {
  listConversationJobs: (payload: ListConversationJobsInput) => Promise<JobRead[]>
  readJob: (jobId: number) => Promise<JobRead>
  rerunAnalysis: (conversationId: number) => Promise<JobRead>
}

export type DesktopSimulationsBridge = {
  create: (payload: SimulationCreate) => Promise<SimulationJobRead>
  listConversationJobs: (payload: ListConversationSimulationJobsInput) => Promise<SimulationJobRead[]>
  read: (simulationId: number) => Promise<SimulationRead>
}

export type DesktopBridge = {
  getServiceState: () => Promise<DesktopServiceState>
  pickImportFile: () => Promise<DesktopFileSelectionPayload>
  pickAvatarFile: () => Promise<DesktopAvatarFilePayload | null>
  getAppInfo: () => Promise<DesktopAppInfo>
  settings: DesktopSettingsBridge
  conversations: DesktopConversationsBridge
  jobs: DesktopJobsBridge
  simulations: DesktopSimulationsBridge
  window: DesktopWindowBridge
}
