"""Delete expired generated audio artifacts."""

from backend.api.audio import cleanup_expired_audio


if __name__ == "__main__":
    result = cleanup_expired_audio()
    print(f"deleted={result.deleted} retained={result.retained}")
