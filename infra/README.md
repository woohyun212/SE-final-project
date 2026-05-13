# 인프라 (Infrastructure)

## 목적

자체 서버 운영 인프라 (Docker · tailscale 메시 VPN · Blue-Green 무중단 배포)

## 현재 산출물

- `루트 docker-compose.prod.yml` — backend 단일 서비스, PR #15 에서 추가 (위치는 그대로 유지 — docker compose 관례)
- `.github/workflows/backend-deploy.yml` — GHCR 이미지 빌드 + 자체 서버 deploy

## 예정 산출물

- `nginx/` — Blue-Green 트래픽 전환을 위한 nginx 설정 (Sprint #5 의 US-21)
- `tailscale/` — 서버 셋업 스크립트 + 키 갱신 문서
- `backup/` — DB 백업 cron 스크립트

## 의존

- ADR-0002 (자체 서버 + tailscale)

## 관련 이슈

- 이슈 #2 폴더 구조의 `/infra` 항목 충족
- NFR2.2 (Blue-Green) 는 Sprint #5 의 US-21 에서 본격 구현
