#!/bin/bash
# Blue-Green 무중단 배포 스크립트
# 사용법: ./infra/deploy.sh [이미지태그]
# 예시:   ./infra/deploy.sh ghcr.io/woohyun212/se-final-project/backend:latest

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.blue-green.yml"
NGINX_CONF="/etc/nginx/sites-enabled/backend.pongchi.kro.kr"
SLOT_FILE="/tmp/se-active-slot"
IMAGE="${1:-ghcr.io/woohyun212/se-final-project/backend:latest}"

# 현재 활성 슬롯 확인
ACTIVE=$(cat "$SLOT_FILE" 2>/dev/null || echo "blue")
if [ "$ACTIVE" = "blue" ]; then
    NEW="green"
    NEW_PORT=8010
    OLD_PORT=8000
else
    NEW="blue"
    NEW_PORT=8000
    OLD_PORT=8010
fi

echo "현재 활성: $ACTIVE → 신규: $NEW (포트 $NEW_PORT)"

# 새 이미지 pull
echo "이미지 pull 중..."
docker pull "$IMAGE"

# 기존 prod 단일 컨테이너가 신규 슬롯 포트(8000)와 충돌할 때만 선제 정리
# (이 경우 nginx 는 ACTIVE 슬롯(8010)을 보고 있으므로 트래픽 영향 없음.
#  최초 전환(NEW=green:8010)에서는 충돌이 없으므로 트래픽 전환 후에 정리한다 — 무중단 유지)
if [ "$NEW_PORT" = "8000" ] && docker ps -q --filter "name=^se-final-project-backend$" | grep -q .; then
    echo "포트 8000 충돌 — 기존 prod 컨테이너 정리..."
    docker stop se-final-project-backend 2>/dev/null || true
    docker rm se-final-project-backend 2>/dev/null || true
fi

# 비활성 슬롯 시작
echo "backend-$NEW 기동 중..."
BACKEND_IMAGE="$IMAGE" docker compose -f "$COMPOSE_FILE" up -d "backend-$NEW"

# 헬스체크 대기 (최대 60초)
echo "헬스체크 대기..."
for i in $(seq 1 12); do
    if curl -sf "http://127.0.0.1:$NEW_PORT/health" > /dev/null 2>&1; then
        echo "✓ backend-$NEW 정상 응답"
        break
    fi
    if [ $i -eq 12 ]; then
        echo "❌ 헬스체크 실패 — 롤백"
        docker stop "se-final-project-backend-$NEW" 2>/dev/null || true
        exit 1
    fi
    sleep 5
done

# nginx 트래픽 전환
echo "nginx 트래픽 전환 → $NEW_PORT..."
sudo sed -i "s/127.0.0.1:[0-9]*/127.0.0.1:$NEW_PORT/" "$NGINX_CONF"
sudo nginx -s reload

# 슬롯 기록
echo "$NEW" > "$SLOT_FILE"

# 구 슬롯 중단 (10초 대기 후 graceful stop)
sleep 10
echo "backend-$ACTIVE 중단..."
docker stop "se-final-project-backend-$ACTIVE" 2>/dev/null || true

# 기존 prod 단일 컨테이너 정리 (blue-green 최초 전환 시 — 트래픽 전환 후라 무중단)
if docker ps -aq --filter "name=^se-final-project-backend$" | grep -q .; then
    echo "기존 prod 컨테이너 정리..."
    docker stop se-final-project-backend 2>/dev/null || true
    docker rm se-final-project-backend 2>/dev/null || true
fi

echo "✅ 배포 완료: $ACTIVE → $NEW"
