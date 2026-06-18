# PPT 스크린샷 캡처

발표 자료용 화면 캡처 세트. 실제 Electron 창에서 **실서버(backend.pongchi.kro.kr)** 와
연동해 회원가입 → 로그인 → 음성 녹음 → 추천 → 이력 전 플로우를 자동으로 찍는다.

## 결과물 (PNG)

| 파일 | 화면 |
| --- | --- |
| `01-signup.png` / `02-signup-filled.png` | 회원가입 (빈 폼 / 입력됨) |
| `03-login.png` / `04-login-filled.png` | 로그인 (빈 폼 / 입력됨) |
| `05-home-idle.png` | 홈 — 음성 녹음 시작 화면 |
| `06-home-recording.png` | 녹음 중 (이퀄라이저 + 타이머 + 진행률) |
| `07-home-analyzing.png` | "음성을 분석하고 음악을 찾는 중…" |
| `08-recommend.png` | 추천 결과 (상단 뷰포트) |
| `08b-recommend-full.png` | 추천 결과 전체 (리스트 + 감정-음악 차트 + 추천 이유) |
| `09-history.png` / `09b-history-full.png` | 추천 이력 |

## 음성 처리 방식

마이크 대신 한국어 TTS WAV(`voice_sample.wav`)를 Chromium 가짜 오디오 장치로 주입한다.
→ `getUserMedia` 가 이 WAV 를 가상 마이크로 반환 → 실제 녹음→`POST /recommend`→
STT/감정분석→추천 까지 진짜로 동작한다 (mock 아님).

`voice_sample.wav` 는 SAPI(Microsoft Heami, ko-KR)로 생성:
"오늘 정말 기분이 좋고 행복해요. 신나는 음악을 듣고 싶어요."
→ 백엔드가 **행복 100%** 로 분석, 신나는 곡 10개 추천.

## 재실행 방법

```powershell
cd client
# 1) .env.local 에 NEXT_PUBLIC_API_BASE_URL=https://backend.pongchi.kro.kr 확인
# 2) 실서버 URL 로 dev 서버 기동
npm run dev:next                       # http://localhost:3000
# 3) 드라이버 실행 (별도 터미널) — 매 실행 새 계정 생성
$env:RUN_STAMP = "ppt$(Get-Date -Format 'MMddHHmmss')"
.\node_modules\electron\dist\electron.exe screenshots\capture.js
```

WAV 재생성이 필요하면:

```powershell
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.SelectVoice("Microsoft Heami Desktop")
$fmt = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(44100,16,1)
$s.SetOutputToWaveFile("screenshots\voice_sample.wav",$fmt)
$s.Speak("오늘 정말 기분이 좋고 행복해요. 신나는 음악을 듣고 싶어요.")
$s.Dispose()
```
