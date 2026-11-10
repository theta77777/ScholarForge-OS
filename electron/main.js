const { app, BrowserWindow, Menu, shell, dialog, ipcMain } = require('electron');
const path = require('path');
const http = require('http');
const { spawn } = require('child_process');

const PORT = process.env.PORT || 8008;
const HOST = '127.0.0.1';
const SERVER_URL = `http://${HOST}:${PORT}`;

let mainWindow = null;
let pythonProcess = null;
let isQuitting = false;

// Check if Python server is already running on port 8008
function checkServerReady(timeoutMs = 1500) {
  return new Promise((resolve) => {
    const req = http.get(`${SERVER_URL}/api/health`, { timeout: timeoutMs }, (res) => {
      resolve(res.statusCode === 200);
    });
    req.on('error', () => resolve(false));
    req.on('timeout', () => {
      req.destroy();
      resolve(false);
    });
  });
}

// Spawn Python FastAPI server if not already running
async function ensureServerRunning() {
  const alreadyRunning = await checkServerReady();
  if (alreadyRunning) {
    console.log(`[ScholarForge Desktop] Existing server detected on ${SERVER_URL}`);
    return;
  }

  console.log(`[ScholarForge Desktop] Spawning Python server daemon...`);
  const projectRoot = path.resolve(__dirname, '..');
  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';

  pythonProcess = spawn(pythonCmd, ['run_server.py'], {
    cwd: projectRoot,
    stdio: 'inherit',
    env: { ...process.env, PORT: String(PORT) }
  });

  pythonProcess.on('error', (err) => {
    console.error('[ScholarForge Desktop] Failed to start Python process:', err);
    dialog.showErrorBox(
      'Python Server Error',
      `Failed to launch ScholarForge backend: ${err.message}\nMake sure Python is installed and accessible in PATH.`
    );
  });

  pythonProcess.on('exit', (code, signal) => {
    if (!isQuitting) {
      console.warn(`[ScholarForge Desktop] Python process exited unexpectedly (code: ${code}, signal: ${signal})`);
    }
  });

  // Wait for server to become healthy
  const startTime = Date.now();
  const maxWait = 25000; // 25 seconds
  while (Date.now() - startTime < maxWait) {
    await new Promise((r) => setTimeout(r, 400));
    const ready = await checkServerReady(800);
    if (ready) {
      console.log(`[ScholarForge Desktop] Server online on ${SERVER_URL}`);
      return;
    }
  }

  throw new Error(`Timeout waiting for ScholarForge server at ${SERVER_URL}`);
}

function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 920,
    minWidth: 1080,
    minHeight: 700,
    title: 'ScholarForge OS — Autonomous Scientific Review Studio',
    backgroundColor: '#020617', // Match Obsidian Slate theme
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      spellcheck: true
    }
  });

  buildAppMenu();

  // Load the web app
  mainWindow.loadURL(SERVER_URL);

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  // Open external links in user's default browser
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('http:') || url.startsWith('https:')) {
      shell.openExternal(url);
      return { action: 'deny' };
    }
    return { action: 'allow' };
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// Native IPC Dialog Handlers
ipcMain.handle('select-storage-folder', async () => {
  if (!mainWindow) return null;
  const result = await dialog.showOpenDialog(mainWindow, {
    title: 'Select Project Storage Folder in Windows Storage',
    properties: ['openDirectory', 'createDirectory']
  });
  if (result.canceled || !result.filePaths || result.filePaths.length === 0) {
    return null;
  }
  return result.filePaths[0];
});

ipcMain.handle('open-path', async (event, targetPath) => {
  if (targetPath) {
    await shell.openPath(targetPath);
    return true;
  }
  return false;
});

function buildAppMenu() {
  const isMac = process.platform === 'darwin';

  const template = [
    ...(isMac ? [{ role: 'appMenu' }] : []),
    {
      label: 'File',
      submenu: [
        {
          label: 'New Review Paper',
          accelerator: 'CmdOrCtrl+N',
          click: () => {
            if (mainWindow) {
              mainWindow.loadURL(SERVER_URL);
            }
          }
        },
        {
          label: 'Open Workspace Directory',
          click: () => {
            const wsPath = path.resolve(__dirname, '..', 'workspace');
            shell.openPath(wsPath);
          }
        },
        { type: 'separator' },
        isMac ? { role: 'close' } : { role: 'quit' }
      ]
    },
    {
      label: 'Edit',
      submenu: [
        { role: 'undo' },
        { role: 'redo' },
        { type: 'separator' },
        { role: 'cut' },
        { role: 'copy' },
        { role: 'paste' },
        { role: 'selectAll' }
      ]
    },
    {
      label: 'View',
      submenu: [
        { role: 'reload' },
        { role: 'forceReload' },
        { role: 'toggleDevTools' },
        { type: 'separator' },
        { role: 'resetZoom' },
        { role: 'zoomIn' },
        { role: 'zoomOut' },
        { type: 'separator' },
        { role: 'togglefullscreen' }
      ]
    },
    {
      label: 'Help',
      submenu: [
        {
          label: 'GitHub Repository',
          click: () => shell.openExternal('https://github.com/theta77777/ScholarForge-OS')
        },
        {
          label: 'Local API Documentation (Swagger)',
          click: () => shell.openExternal(`${SERVER_URL}/docs`)
        },
        { type: 'separator' },
        {
          label: 'About ScholarForge OS',
          click: () => {
            dialog.showMessageBox(mainWindow, {
              type: 'info',
              title: 'About ScholarForge OS',
              message: 'ScholarForge OS v2.2.0',
              detail: 'Autonomous PhD-Grade Scientific Review Paper Engine & Desktop Research Workbench.\n\nRunning locally with native Electron presentation.'
            });
          }
        }
      ]
    }
  ];

  const menu = Menu.buildFromTemplate(template);
  Menu.setApplicationMenu(menu);
}

// App lifecycle
app.whenReady().then(async () => {
  try {
    await ensureServerRunning();
    createMainWindow();

    app.on('activate', () => {
      if (BrowserWindow.getAllWindows().length === 0) {
        createMainWindow();
      }
    });
  } catch (err) {
    console.error('[ScholarForge Desktop] Startup error:', err);
    dialog.showErrorBox('Startup Failure', err.message);
    app.quit();
  }
});

function cleanupPython() {
  if (pythonProcess && !pythonProcess.killed) {
    console.log('[ScholarForge Desktop] Terminating child Python process...');
    try {
      if (process.platform === 'win32') {
        spawn('taskkill', ['/pid', pythonProcess.pid, '/f', '/t']);
      } else {
        pythonProcess.kill('SIGTERM');
      }
    } catch (e) {
      console.warn('[ScholarForge Desktop] Process termination note:', e);
    }
  }
}

app.on('before-quit', () => {
  isQuitting = true;
  cleanupPython();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

