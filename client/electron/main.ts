import { app, BrowserWindow, session, systemPreferences } from 'electron';
import path from 'path';

const isDev = process.env.NODE_ENV === 'development';

function createWindow(): void {
  const mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  if (isDev) {
    void mainWindow.loadURL('http://localhost:3000');
    mainWindow.webContents.openDevTools();
  } else {
    void mainWindow.loadFile(path.join(__dirname, '../out/index.html'));
  }
}

app.whenReady().then(async () => {
  if (process.platform === 'darwin') {
    await systemPreferences.askForMediaAccess('microphone');
  }

  session.defaultSession.setPermissionRequestHandler((_webContents, permission, callback) => {
    callback(permission === 'media');
  });

  session.defaultSession.setPermissionCheckHandler((_webContents, permission) =>
    permission === 'media'
  );

  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
