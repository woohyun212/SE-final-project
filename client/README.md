# Client — Electron + Next.js 보일러플레이트

ADR-0001(Electron 클라이언트) · ADR-0002(Next.js 추가) 결정에 따른 최소 보일러플레이트입니다.  
Next.js **static export → Electron loadFile** 패턴을 사용합니다 (Nextron 미사용, 의존성 최소화).

---

## 사전 요구사항

- Node.js 20 이상
- 개발 모드에서 `/health` 엔드포인트 확인을 위해 백엔드가 `http://localhost:8000` 에서 실행 중이어야 합니다.

## 설치

```bash
npm install
```

## 개발 모드

```bash
npm run dev
```

Next.js 개발 서버(`http://localhost:3000`)와 Electron 창이 동시에 실행됩니다.  
`wait-on`이 Next.js가 준비될 때까지 기다린 뒤 Electron을 실행합니다.

## 프로덕션 빌드

```bash
npm run build   # Next.js static export + Electron TypeScript 컴파일
npm start       # 빌드 후 Electron 실행
```

## 디렉터리 구조

```
client/
├── electron/
│   ├── main.ts        # Electron 메인 프로세스
│   ├── preload.ts     # contextBridge 플레이스홀더 (현재 API 미노출)
│   └── tsconfig.json  # Electron용 TypeScript 설정 (CommonJS)
├── pages/
│   ├── _app.tsx       # Next.js 커스텀 App
│   └── index.tsx      # Hello World + 백엔드 /health 표시
├── styles/
│   └── globals.css    # 최소 리셋 + 다크/라이트 모드 지원
├── next.config.js     # output: 'export' 설정
├── package.json
└── tsconfig.json      # Next.js용 TypeScript 설정
```

## 다음 단계

Sprint #1 **US-3** — 음성 녹음 컴포넌트 작업 예정.  
`electron/preload.ts` 에서 `contextBridge.exposeInMainWorld()` 로 필요한 API를 안전하게 노출합니다.
