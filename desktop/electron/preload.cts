const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('desktop', {
  getServiceState: () => ipcRenderer.invoke('desktop:get-service-state'),
  pickImportFile: () => ipcRenderer.invoke('desktop:pick-import-file'),
  getAppInfo: () => ipcRenderer.invoke('desktop:get-app-info'),
  readImportFile: () => ipcRenderer.invoke('desktop:read-import-file'),
  window: {
    minimize: () => ipcRenderer.invoke('desktop:window-minimize'),
    toggleMaximize: () => ipcRenderer.invoke('desktop:window-toggle-maximize'),
    close: () => ipcRenderer.invoke('desktop:window-close'),
    getState: () => ipcRenderer.invoke('desktop:window-get-state'),
  },
})
