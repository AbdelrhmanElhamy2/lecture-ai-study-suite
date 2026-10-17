import json
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, patch

import config
import pipeline
import transcription
from mock_generator import get_sample_bilingual_lecture_guide
from models import VerificationResult


class TestHybridTranscription(unittest.TestCase):
    def setUp(self):
        transcription._model = None
        transcription._model_key = None

    def tearDown(self):
        transcription._model = None
        transcription._model_key = None

    def test_transcriber_consumes_segments_caches_model_and_preserves_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "first.mp3"
            second = Path(tmp) / "second.mp3"
            first.write_bytes(b"first")
            second.write_bytes(b"second")
            calls = []

            class FakeModel:
                def transcribe(self, path, **kwargs):
                    calls.append((Path(path).name, kwargs))
                    def lazy_segments():
                        yield SimpleNamespace(start=0.25, end=1.5, text=" Power electronics")
                        yield SimpleNamespace(start=1.5, end=2.0, text=" lecture")
                    return lazy_segments(), SimpleNamespace(language="ar", language_probability=0.91)

            factory = MagicMock(return_value=FakeModel())
            result = transcription.transcribe_audio_sources([first, second], model_factory=factory)
            self.assertEqual([item.source_index for item in result], [1, 2])
            self.assertEqual([item.text for item in result], ["Power electronics lecture"] * 2)
            self.assertEqual(result[0].segments[0].start, 0.25)
            self.assertEqual(result[0].segments[1].end, 2.0)
            self.assertEqual(result[0].language, "ar")
            self.assertAlmostEqual(result[0].language_probability, 0.91)
            self.assertEqual([c[0] for c in calls], ["first.mp3", "second.mp3"])
            self.assertTrue(all(c[1]["language"] is None for c in calls))
            self.assertEqual(factory.call_count, 1)

    def test_concurrent_first_use_initializes_one_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "concurrent.wav"
            path.write_bytes(b"audio")

            class FakeModel:
                def transcribe(self, _path, **_kwargs):
                    return iter([SimpleNamespace(start=0, end=1, text="speech")]), SimpleNamespace(language="en", language_probability=1)

            def make_model(*_args, **_kwargs):
                time.sleep(0.05)
                return FakeModel()

            factory = MagicMock(side_effect=make_model)
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda _n: transcription.transcribe_audio_sources([path], model_factory=factory), range(2)))
            self.assertEqual(factory.call_count, 1)
            self.assertEqual([result[0].text for result in results], ["speech", "speech"])

    def test_empty_audio_and_empty_transcript_are_readable_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            empty = Path(tmp) / "empty.wav"
            empty.touch()
            with self.assertRaisesRegex(ValueError, "empty"):
                transcription.transcribe_audio_sources([empty], model_factory=MagicMock())

            valid = Path(tmp) / "silent.wav"
            valid.write_bytes(b"audio")
            transcription._model = None
            transcription._model_key = None
            fake_model = MagicMock()
            fake_model.transcribe.return_value = (iter(()), SimpleNamespace(language="en", language_probability=0.8))
            with self.assertRaisesRegex(ValueError, "empty transcript"):
                transcription.transcribe_audio_sources([valid], model_factory=MagicMock(return_value=fake_model))

    def test_model_initialization_error_explains_first_download_without_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "lecture.wav"
            path.write_bytes(b"audio")
            factory = MagicMock(side_effect=OSError("download failure"))
            with self.assertRaisesRegex(RuntimeError, "internet connection") as caught:
                transcription.transcribe_audio_sources([path], model_factory=factory)
            self.assertNotIn(tmp, str(caught.exception))

    def test_gemini_policy_allows_only_primary_and_configured_fallback(self):
        self.assertEqual(config.PRIMARY_GEMINI_MODEL, "gemini-3.8-flash")
        self.assertEqual(config.FALLBACK_GEMINI_MODEL, "gemini-3.6-flash")
        self.assertEqual(config.default_gemini_model(), "gemini-3.8-flash")
        self.assertEqual(config.default_gemini_model("gemini-3.7-flash"), "gemini-3.8-flash")
        self.assertEqual(config.gemini_model_candidates("gemini-3.8-flash"), ["gemini-3.8-flash", "gemini-3.6-flash"])
        self.assertEqual(config.gemini_model_candidates("gemini-3.6-flash"), ["gemini-3.6-flash"])
        for disallowed in ("gemini-3.5-flash", "gemini-3.7-flash", "gemini-flash-latest"):
            with self.assertRaises(ValueError):
                config.resolve_gemini_model(disallowed)
        self.assertEqual(config.gemini_model_candidates(), [config.DEFAULT_MODEL, "gemini-3.6-flash"] if config.DEFAULT_MODEL == "gemini-3.8-flash" else [config.DEFAULT_MODEL])

    def test_runtime_model_ui_env_and_docs_are_consistent(self):
        root = Path(__file__).resolve().parents[1]
        ui = (root / "templates" / "index.html").read_text(encoding="utf-8")
        env_example = (root / ".env.example").read_text(encoding="utf-8")
        readme = (root / "README.md").read_text(encoding="utf-8")
        self.assertIn('value="gemini-3.8-flash"', ui)
        self.assertIn('value="gemini-3.6-flash"', ui)
        self.assertNotIn('value="gemini-3.5-flash"', ui)
        self.assertNotIn('value="gemini-3.7-flash"', ui)
        self.assertIn("GEMINI_MODEL=gemini-3.8-flash", env_example)
        self.assertIn("gemini-3.8-flash", readme)
        self.assertIn("gemini-3.6-flash", readme)
        self.assertIn("LECTUREAI_WHISPER_MODEL=small", env_example)

    def test_generation_sends_transcript_not_audio_and_uses_bounded_fallback(self):
        import pedagogy_engine
        guide = get_sample_bilingual_lecture_guide()
        verification = VerificationResult(
            contradictions_detected=0,
            audit_summary="Transcript check complete.",
            corrected_guide=guide,
        )
        responses = [
            SimpleNamespace(text=guide.model_dump_json()),
            SimpleNamespace(text=verification.model_dump_json()),
        ]
        client = MagicMock()
        client.models.generate_content.side_effect = [RuntimeError("503 UNAVAILABLE"), RuntimeError("503 UNAVAILABLE"), *responses]
        transcript = "[Recording 1; detected language: ar]\n[0.25-1.50] MOSFET switching frequency"
        with patch("pedagogy_engine.genai.Client", return_value=client), patch("pedagogy_engine.time.sleep"):
            result = pedagogy_engine.analyze_lecture_transcript(transcript, api_key="unit-test-key", model="gemini-3.8-flash")
        self.assertIsNotNone(result)
        requested_models = [call.kwargs["model"] for call in client.models.generate_content.call_args_list]
        self.assertEqual(requested_models, ["gemini-3.8-flash", "gemini-3.8-flash", "gemini-3.6-flash", "gemini-3.6-flash"])
        self.assertFalse(any(model in {"gemini-3.5-flash", "gemini-3.7-flash"} for model in requested_models))
        payloads = [call.kwargs["contents"] for call in client.models.generate_content.call_args_list]
        self.assertTrue(all(any(transcript in item for item in payload if isinstance(item, str)) for payload in payloads))
        self.assertTrue(all(b"audio" not in payload for payload in payloads if isinstance(payload, bytes)))
        client.files.upload.assert_not_called()

    def test_demo_skips_whisper_and_gemini(self):
        class Builder:
            def __init__(self, guide, **kwargs):
                self.guide = guide

            def build(self):
                return Path(tempfile.gettempdir()) / "mock-demo.pdf"

        with patch("pipeline.transcribe_audio_sources", side_effect=AssertionError("Whisper called")), \
             patch("pipeline.analyze_lecture_transcript", side_effect=AssertionError("Gemini path called")), \
             patch("pipeline.PDFStudyGuideBuilder", Builder):
            result = pipeline.process_lecture(use_sample_demo=True)
        self.assertTrue(result["is_demo"])
        self.assertTrue(result["guide"]["verification_report"]["is_simulation"])
        self.assertIn("Simulated", result["verification_report"]["overall_fidelity_summary"])

    def test_pipeline_transcribes_before_generation_and_stops_on_local_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            audio = Path(tmp) / "private-recording.wav"
            audio.write_bytes(b"synthetic fixture")
            local_result = [transcription.SourceTranscript(
                source_index=1,
                text="switching frequency is ten kilohertz",
                segments=[transcription.TranscriptSegment(0.0, 1.25, "switching frequency is ten kilohertz")],
                language="en",
                language_probability=0.98,
            )]
            generated = get_sample_bilingual_lecture_guide()
            with patch("pipeline.transcribe_audio_sources", return_value=local_result) as transcribe, \
                 patch("pipeline.analyze_lecture_transcript", return_value=generated) as analyze, \
                 patch("pipeline.PDFStudyGuideBuilder") as builder:
                builder.return_value.build.return_value = Path(tmp) / "guide.pdf"
                pipeline.process_lecture(audio_path=[audio], api_key="test-key")
            transcribe.assert_called_once()
            self.assertEqual(analyze.call_args.kwargs["transcript_text"].count("switching frequency"), 1)
            self.assertNotIn("audio_path", analyze.call_args.kwargs)
            self.assertNotIn(str(audio), str(analyze.call_args.kwargs))

            with patch("pipeline.transcribe_audio_sources", side_effect=ValueError("local transcription failed")), \
                 patch("pipeline.analyze_lecture_transcript") as analyze:
                with self.assertRaisesRegex(ValueError, "local transcription failed"):
                    pipeline.process_lecture(audio_path=[audio], api_key="test-key")
                analyze.assert_not_called()

    def test_gemini_key_is_preflighted_before_local_model_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            audio = Path(tmp) / "recording.wav"
            audio.write_bytes(b"audio")
            with patch("pipeline.get_gemini_api_key", return_value=""), \
                 patch("pipeline.transcribe_audio_sources") as transcribe:
                with self.assertRaisesRegex(ValueError, "Gemini API key is required"):
                    pipeline.process_lecture(audio_path=[audio], api_key=None)
                transcribe.assert_not_called()

    def test_job_error_redacts_key_paths_and_signed_links(self):
        from app import safe_public_error
        message = safe_public_error(r"Key secret-token failed at C:\private\lecture.mp3 https://example.test/file?token=secret-token", "secret-token")
        self.assertNotIn("secret-token", message)
        self.assertNotIn("C:\\private", message)
        self.assertNotIn("https://", message)


if __name__ == "__main__":
    unittest.main()
