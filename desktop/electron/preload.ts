import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('desktop', {
  getServiceState: () => ipcRenderer.invoke('desktop:get-service-state'),
})
