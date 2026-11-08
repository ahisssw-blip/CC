import asyncio

from src import media


def test_flood_wait_retries_are_bounded(monkeypatch, tmp_path):
    class FakeFloodWait(Exception):
        seconds = 1

    class FakeMessage:
        media = object()

    class AlwaysRateLimitedClient:
        calls = 0

        async def download_media(self, *args, **kwargs):
            self.calls += 1
            raise FakeFloodWait("rate limited")

    client = AlwaysRateLimitedClient()
    async def no_wait(_seconds):
        return None

    monkeypatch.setattr(media, "FloodWaitError", FakeFloodWait)
    monkeypatch.setattr(media.asyncio, "sleep", no_wait)
    result = asyncio.run(media.download_media_safely(
        client, FakeMessage(), "video.bin", video_dir=str(tmp_path)
    ))

    assert result["success"] is False
    assert client.calls == media.MEDIA_DOWNLOAD_RETRY + 1
