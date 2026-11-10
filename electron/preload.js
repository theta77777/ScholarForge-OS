const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  isElectron: true,
  selectStorageFolder: () => ipcRenderer.invoke('select-storage-folder'),
  openPath: (targetPath) => ipcRenderer.invoke('open-path', targetPath)
});

