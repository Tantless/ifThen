import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('desktop', {
  getServiceState: () => ipcRenderer.invoke('desktop:get-service-state'),
  pickImportFile: () => ipcRenderer.invoke('desktop:pick-import-file'),
  getAppInfo: () => ipcRenderer.invoke('desktop:get-app-info'),
  readImportFile: () => ipcRenderer.invoke('desktop:read-import-file'),
})
