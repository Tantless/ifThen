// @ts-nocheck

const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('desktop', {
  getServiceState: () => ipcRenderer.invoke('desktop:get-service-state'),
  pickImportFile: () => ipcRenderer.invoke('desktop:pick-import-file'),
  pickAvatarFile: () => ipcRenderer.invoke('desktop:pick-avatar-file'),
  getAppInfo: () => ipcRenderer.invoke('desktop:get-app-info'),
  settings: {
    read: () => ipcRenderer.invoke('desktop:settings-read'),
    /** @param {import('../src/types/api.js').SettingWrite} payload */
    write: (payload) => ipcRenderer.invoke('desktop:settings-write', payload),
  },
  conversations: {
    list: () => ipcRenderer.invoke('desktop:conversations-list'),
    /** @param {number} conversationId */
    delete: (conversationId) => ipcRenderer.invoke('desktop:conversations-delete', conversationId),
    /** @param {import('../src/types/api.js').ListMessagesInput} payload */
    listMessages: (payload) => ipcRenderer.invoke('desktop:conversations-list-messages', payload),
    /** @param {number} conversationId */
    listMessageDays: (conversationId) => ipcRenderer.invoke('desktop:conversations-list-message-days', conversationId),
    /** @param {number} conversationId */
    listTopics: (conversationId) => ipcRenderer.invoke('desktop:conversations-list-topics', conversationId),
    /** @param {number} conversationId */
    readProfile: (conversationId) => ipcRenderer.invoke('desktop:conversations-read-profile', conversationId),
    /** @param {import('../src/types/api.js').ReadSnapshotInput} payload */
    readSnapshot: (payload) => ipcRenderer.invoke('desktop:conversations-read-snapshot', payload),
    /** @param {import('../src/types/api.js').ImportConversationRequest} payload */
    import: (payload) => ipcRenderer.invoke('desktop:conversations-import', payload),
    /** @param {number} conversationId */
    startAnalysis: (conversationId) => ipcRenderer.invoke('desktop:conversations-start-analysis', conversationId),
  },
  jobs: {
    /** @param {import('../src/types/api.js').ListConversationJobsInput} payload */
    listConversationJobs: (payload) => ipcRenderer.invoke('desktop:jobs-list-conversation', payload),
    /** @param {number} jobId */
    readJob: (jobId) => ipcRenderer.invoke('desktop:jobs-read', jobId),
    /** @param {number} conversationId */
    rerunAnalysis: (conversationId) => ipcRenderer.invoke('desktop:jobs-rerun-analysis', conversationId),
  },
  simulations: {
    /** @param {import('../src/types/api.js').SimulationCreate} payload */
    create: (payload) => ipcRenderer.invoke('desktop:simulations-create', payload),
    /** @param {import('../src/types/api.js').ListConversationSimulationJobsInput} payload */
    listConversationJobs: (payload) =>
      ipcRenderer.invoke('desktop:simulations-list-conversation-jobs', payload),
    /** @param {number} simulationId */
    read: (simulationId) => ipcRenderer.invoke('desktop:simulations-read', simulationId),
  },
  window: {
    minimize: () => ipcRenderer.invoke('desktop:window-minimize'),
    toggleMaximize: () => ipcRenderer.invoke('desktop:window-toggle-maximize'),
    close: () => ipcRenderer.invoke('desktop:window-close'),
    getState: () => ipcRenderer.invoke('desktop:window-get-state'),
  },
})
