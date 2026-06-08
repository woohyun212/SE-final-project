const nextJest = require('next/jest');

const createJestConfig = nextJest({ dir: './' });

/** @type {import('jest').Config} */
const customJestConfig = {
  setupFilesAfterEnv: ['<rootDir>/jest.setup.ts'],
  testEnvironment: 'jest-environment-jsdom',
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/$1',
  },
  // 커버리지 대상: lib/ · components/ 전역 (NFR4.4 ≥70%). 타입 선언은 제외.
  collectCoverageFrom: [
    'lib/**/*.{ts,tsx}',
    'components/**/*.{ts,tsx}',
    '!**/*.d.ts',
  ],
  // 게이트는 NFR4.4(≥70%) 를 충족하며, 현 실측(라인 95%/브랜치 87%)보다
  // 보수적으로 잡아 사소한 변동에 깨지지 않게 한다. 신규 코드가 무테스트로
  // 들어오면 이 게이트가 CI(test:coverage)에서 막는다.
  coverageThreshold: {
    global: { branches: 75, functions: 85, lines: 85, statements: 85 },
  },
  testMatch: ['**/__tests__/**/*.test.{ts,tsx}'],
};

module.exports = createJestConfig(customJestConfig);
