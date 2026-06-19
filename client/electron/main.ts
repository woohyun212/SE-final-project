import { app, BrowserWindow, protocol, net, session, systemPreferences } from 'electron';
import path from 'path';
import { pathToFileURL } from 'url';

const isDev = process.env.NODE_ENV === 'development';

// 정적 export(out/) 의 루트. 프로덕션에서 app:// 프로토콜로 서빙한다.
const OUT_DIR = path.join(__dirname, '..', 'out');

// app:// 를 특권 스킴으로 등록 — http 처럼 동작(보안 컨텍스트/fetch/표준 URL 파싱)해야
// Next 클라이언트 라우팅(router.push)이 file:// 의 제약 없이 정상 동작한다.
// (file:// 로드 시 trailingSlash export 라우트 전환이 깨져 흰 화면이 되는 문제 해결.)
protocol.registerSchemesAsPrivileged([
  {
    scheme: 'app',
    privileges: { standard: true, secure: true, supportFetchAPI: true },
  },
]);

/**
 * app://./ 요청 경로를 out/ 안의 실제 파일로 매핑한다.
 * - trailingSlash export: `/`, `/login`, `/login/` → `<dir>/index.html`
 * - 정적 에셋(`/_next/...`, 이미지 등)은 그대로 전달
 * - 매칭 실패 시 404.html
 */
function resolveAppPath(requestPath: string): string {
  // 선행 슬래시 제거 + 쿼리/해시 잘라내기.
  let p = decodeURIComponent(requestPath.split('?')[0].split('#')[0]);
  p = p.replace(/^\/+/, '');

  const candidate = path.join(OUT_DIR, p);
  const ext = path.extname(candidate);

  if (ext) {
    // 확장자가 있으면 파일 그대로(에셋/html).
    return candidate;
  }
  // 확장자가 없으면 디렉터리 라우트 → <route>/index.html
  return path.join(candidate, 'index.html');
}

function createWindow(): void {
  const mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      // 데스크톱 앱(app://)은 백엔드와 항상 cross-origin 이라 브라우저 CORS preflight
      // 가 막힌다(백엔드 CORS 화이트리스트에 데스크톱 origin 이 없음). 로컬 신뢰 코드만
      // 로드하는 패키징 앱이므로 webSecurity 를 꺼 CORS 강제를 비활성화한다.
      // (dev 모드는 http://localhost:3000 origin 이 백엔드 화이트리스트에 있어 불필요.)
      webSecurity: isDev ? true : false,
    },
  });

  if (isDev) {
    void mainWindow.loadURL('http://localhost:3000');
    mainWindow.webContents.openDevTools();
  } else {
    void mainWindow.loadURL('app://./');
  }
}

app.whenReady().then(async () => {
  if (process.platform === 'darwin') {
    await systemPreferences.askForMediaAccess('microphone');
  }

  // 프로덕션: app:// 핸들러 등록 (out/ 서빙).
  if (!isDev) {
    protocol.handle('app', async (request) => {
      const { pathname } = new URL(request.url);
      let filePath = resolveAppPath(pathname);

      // 1차 매칭 파일이 없으면 404.html 로 폴백.
      const fileUrl = pathToFileURL(filePath).toString();
      const res = await net.fetch(fileUrl).catch(() => null);
      if (res && res.ok) return res;

      const notFound = pathToFileURL(path.join(OUT_DIR, '404.html')).toString();
      return net.fetch(notFound);
    });
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
