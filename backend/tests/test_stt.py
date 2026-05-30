"""STT 서비스 단위 테스트 — faster-whisper 모델은 mock으로 대체."""

from unittest.mock import MagicMock

from app.services.stt import LocalWhisperProvider, STTProvider, get_stt_provider


# ── 프로토콜 ──────────────────────────────────────────────────────────────────


def test_local_whisper_satisfies_protocol():
    assert isinstance(LocalWhisperProvider(), STTProvider)


# ── 헬퍼 ──────────────────────────────────────────────────────────────────────


def _mock_model(*texts: str) -> MagicMock:
    """지정한 텍스트를 반환하는 WhisperModel mock 생성."""
    segments = []
    for t in texts:
        seg = MagicMock()
        seg.text = t
        segments.append(seg)
    model = MagicMock()
    model.transcribe.return_value = (iter(segments), MagicMock())
    return model


def _provider_with_model(*texts: str) -> LocalWhisperProvider:
    """모델이 이미 로드된 상태의 provider 반환."""
    provider = LocalWhisperProvider()
    provider._load_model = MagicMock()
    provider._model = _mock_model(*texts)
    return provider


# ── 빈 오디오 ─────────────────────────────────────────────────────────────────


async def test_empty_bytes_returns_empty_string():
    result = await LocalWhisperProvider().transcribe(b"", "test.wav")
    assert result == ""


# ── 정상 변환 ─────────────────────────────────────────────────────────────────


async def test_transcribe_joins_multiple_segments():
    provider = _provider_with_model(" 안녕하세요 ", " 반갑습니다 ")
    result = await provider.transcribe(b"audio", "test.wav")
    assert result == "안녕하세요 반갑습니다"


async def test_transcribe_strips_whitespace():
    provider = _provider_with_model("  오늘 날씨 좋다  ")
    result = await provider.transcribe(b"audio", "test.wav")
    assert result == "오늘 날씨 좋다"


async def test_transcribe_empty_segments_returns_empty():
    provider = _provider_with_model()  # 세그먼트 없음
    result = await provider.transcribe(b"silence", "silence.wav")
    assert result == ""


async def test_transcribe_calls_model_with_language():
    provider = _provider_with_model("test")
    await provider.transcribe(b"audio", "test.wav")

    _, kwargs = provider._model.transcribe.call_args
    assert kwargs.get("language") == "ko"


# ── 모델 로딩 ─────────────────────────────────────────────────────────────────


def test_model_not_loaded_at_init():
    assert LocalWhisperProvider()._model is None


def test_load_model_called_once(monkeypatch):
    mock_cls = MagicMock(return_value=MagicMock())
    monkeypatch.setattr("faster_whisper.WhisperModel", mock_cls, raising=False)

    provider = LocalWhisperProvider(model_size="tiny")
    provider._load_model()
    provider._load_model()  # 두 번 호출해도

    mock_cls.assert_called_once()  # 모델 생성은 1회


def test_load_model_uses_correct_size(monkeypatch):
    mock_cls = MagicMock(return_value=MagicMock())
    monkeypatch.setattr("faster_whisper.WhisperModel", mock_cls, raising=False)

    LocalWhisperProvider(model_size="medium")._load_model()

    assert mock_cls.call_args[0][0] == "medium"


# ── 싱글톤 ────────────────────────────────────────────────────────────────────


def test_get_stt_provider_returns_same_instance(monkeypatch):
    import app.services.stt as stt_module
    monkeypatch.setattr(stt_module, "_provider", None)

    assert get_stt_provider() is get_stt_provider()


def test_get_stt_provider_respects_env_var(monkeypatch):
    import app.services.stt as stt_module
    monkeypatch.setattr(stt_module, "_provider", None)
    monkeypatch.setenv("WHISPER_MODEL_SIZE", "base")

    provider = get_stt_provider()

    assert isinstance(provider, LocalWhisperProvider)
    assert provider._model_size == "base"

    monkeypatch.setattr(stt_module, "_provider", None)
