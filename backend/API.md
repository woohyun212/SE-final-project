# Backend API 명세

Base URL: `http://localhost:8000`

---

## Health

| Method | Path | 인증 |
|--------|------|------|
| GET | `/health` | 불필요 |

**Response** `200`
```json
{ "message": "Hello World" }
```

---

## Auth `/auth`

### POST `/auth/signup`
회원가입. 성공 시 access/refresh token 즉시 발급.

**Request Body**
```json
{ "email": "user@example.com", "password": "abc12345" }
```
> 비밀번호: 8자 이상, 영문 + 숫자 필수

**Response** `201`
```json
{
  "access_token": "<JWT>",
  "refresh_token": "<token>",
  "token_type": "bearer"
}
```

**Errors** `409` 이메일 중복

---

### POST `/auth/login`
로그인.

**Request Body**
```json
{ "email": "user@example.com", "password": "abc12345" }
```

**Response** `200` — signup과 동일 구조

**Errors** `401` 이메일/비밀번호 불일치, 비활성 계정

---

### POST `/auth/logout`
로그아웃. refresh token 무효화.

**Headers** `Authorization: Bearer <access_token>`

**Request Body**
```json
{ "refresh_token": "<token>" }
```

**Response** `204 No Content`

---

### POST `/auth/refresh`
Access token 재발급. Refresh token은 1회 사용 후 폐기.

**Request Body**
```json
{ "refresh_token": "<token>" }
```

**Response** `200`
```json
{ "access_token": "<JWT>", "token_type": "bearer" }
```

**Errors** `401` 만료되거나 유효하지 않은 refresh token

---

## Recommend `/recommend`

### POST `/recommend`
감정 벡터 기반 음악 추천. MusicCatalog DB에서 코사인 유사도로 상위 10곡 반환.

**Content-Type** `multipart/form-data`

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `audio` | file | 필수 | 음성 파일 |
| `valence` | float | 0.5 | 긍정/부정 감정 (0.0~1.0) |
| `energy` | float | 0.5 | 에너지 (0.0~1.0) |
| `danceability` | float | 0.5 | 댄서빌리티 (0.0~1.0) |
| `acousticness` | float | 0.5 | 어쿠스틱 정도 (0.0~1.0) |
| `instrumentalness` | float | 0.5 | 보컬 없는 정도 (0.0~1.0) |

**Response** `200`
```json
{
  "tracks": [
    {
      "track_id": "spotify_track_id",
      "title": "곡 제목",
      "artist": "아티스트",
      "album": "앨범",
      "duration_sec": 213,
      "preview_url": "https://..." // nullable
    }
  ]
}
```

## 인증 방식

JWT Bearer Token (HS256). Access token 유효기간 60분, Refresh token 30일.

```
Authorization: Bearer <access_token>
```
