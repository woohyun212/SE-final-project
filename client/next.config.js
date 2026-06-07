/** @type {import('next').NextConfig} */

// Electron 패키지 빌드(`ELECTRON_BUILD=1`) 시에는 file:// 로 로드되므로
// 에셋 경로를 상대(`./`)로 바꿔 `/_next/...` 절대경로가 깨지지 않게 한다.
// 웹/개발 빌드에는 영향이 없다.
const isElectron = process.env.ELECTRON_BUILD === '1';

const nextConfig = {
  output: 'export',
  images: { unoptimized: true },
  trailingSlash: true,
  ...(isElectron ? { assetPrefix: './' } : {}),
};
module.exports = nextConfig;
