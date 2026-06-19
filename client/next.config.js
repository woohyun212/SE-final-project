/** @type {import('next').NextConfig} */

// Electron 프로덕션 빌드는 커스텀 app:// 프로토콜(electron/main.ts)로 out/ 을
// 서빙한다. app:// 는 http 처럼 절대경로(`/_next/...`)를 정상 해석하므로 별도
// assetPrefix 우회가 필요 없다. (과거 file:// 로드 시 쓰던 assetPrefix:'./' 는
// 중첩 라우트에서 상대경로가 깨져 제거함.)
const nextConfig = {
  output: 'export',
  images: { unoptimized: true },
  trailingSlash: true,
};
module.exports = nextConfig;
