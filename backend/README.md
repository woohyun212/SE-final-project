# 백엔드

FastAPI 기반 최소 백엔드 서버입니다.

## 로컬 실행

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

헬스 체크:

```bash
curl http://127.0.0.1:8000/health
```

응답:

```json
{"message":"Hello World"}
```

## Docker 실행

```bash
docker build -t se-final-project-backend ./backend
docker run --rm -p 8000:8000 se-final-project-backend
```

## GitHub Actions 배포

배포 방식은 ADR-0002의 결정에 맞춰 **GHCR Docker 이미지 + 자체 서버 docker compose**를 기준으로 한다.
`main` 브랜치에 백엔드 변경이 push되면 테스트 후 이미지를 빌드/푸시하고, 서버에서 컨테이너를 갱신한다.

GitHub 저장소 설정에 다음 값을 등록해야 한다.

Secrets:

- `DEPLOY_HOST`: tailscale 또는 SSH로 접근 가능한 서버 주소
- `DEPLOY_USER`: 배포 서버 사용자
- `DEPLOY_SSH_KEY`: 배포 서버 접속용 private key
- `DEPLOY_PATH`: 서버의 배포 디렉터리
- `GHCR_USER`: GHCR 이미지를 pull할 GitHub 사용자명
- `GHCR_TOKEN`: `read:packages` 권한이 있는 GitHub token. GHCR 패키지를 public으로 열면 생략 가능

Variables:

- `BACKEND_PORT`: 외부에 열 포트. 기본값은 `8000`

