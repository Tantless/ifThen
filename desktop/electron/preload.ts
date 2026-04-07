import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('desktop', {
  getServiceState: () => ipcRenderer.invoke('desktop:get-service-state'),
  getAppInfo: () => ipcRenderer.invoke('desktop:get-app-info'),
  restartBackend: () => ipcRenderer.invoke('desktop:restart-backend'),
})
