import threading

from core.estimation_service import EstimationService
from core.state_manager import TranslationState


class FailingMKVHandler:
    def get_subtitle_tracks(self, _path):
        raise AssertionError("External subtitles must not query MKV tracks")

    def extract_subtitle(self, *_args, **_kwargs):
        raise AssertionError("External subtitles must not be extracted from the MKV")


def test_external_subtitle_estimation_reads_file_directly(tmp_path):
    subtitle = tmp_path / "external.srt"
    subtitle.write_text(
        "1\n00:00:01,000 --> 00:00:02,000\nHello\n\n"
        "2\n00:00:03,000 --> 00:00:04,000\nWorld\n",
        encoding="utf-8",
    )
    completed = threading.Event()
    result = []

    service = EstimationService(FailingMKVHandler())
    started = service.estimate_tokens_async(
        "video.mkv",
        -1,
        lambda chars, lines: (result.append((chars, lines)), completed.set()),
        lambda error: (_ for _ in ()).throw(error),
        external_subtitle_path=str(subtitle),
    )

    assert started is True
    assert completed.wait(2)
    assert result == [(10, 2)]


def test_old_translation_state_remains_compatible():
    state = TranslationState.from_dict(
        {
            "source_file": "video.mkv",
            "source_file_hash": "hash",
            "track_id": 2,
            "source_lang": "English",
            "target_lang": "Indonesian",
            "model_name": "model",
            "total_lines": 1,
            "completed_translations": [],
            "current_batch_index": 0,
        }
    )

    assert state.external_subtitle_path is None
