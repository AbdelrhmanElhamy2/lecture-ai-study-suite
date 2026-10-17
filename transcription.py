"""Local, lazy faster-whisper transcription service."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Callable, Optional, Sequence

from config import WHISPER_COMPUTE_TYPE, WHISPER_DEVICE, WHISPER_MODEL

logger = logging.getLogger(__name__)
_model_lock = threading.Lock()
_model: Any = None
_model_key: Optional[tuple[str, str, str]] = None


@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str


@dataclass
class SourceTranscript:
    source_index: int
    text: str
    segments: list[TranscriptSegment]
    language: Optional[str] = None
    language_probability: Optional[float] = None


def _get_model(model_name: str, device: str, compute_type: str, factory: Optional[Callable[..., Any]] = None):
    global _model, _model_key
    key = (model_name, device, compute_type)
    if _model is not None and _model_key == key:
        return _model
    with _model_lock:
        if _model is not None and _model_key == key:
            return _model
        try:
            if factory is None:
                from faster_whisper import WhisperModel
                factory = WhisperModel
            _model = factory(model_name, device=device, compute_type=compute_type)
            _model_key = key
            return _model
        except ImportError as exc:
            raise RuntimeError("Local transcription needs faster-whisper. Install project dependencies with: pip install -r requirements.txt") from exc
        except Exception as exc:
            logger.warning("Local Whisper model initialization failed (%s/%s).", model_name, device)
            raise RuntimeError(
                f"Could not load the local Whisper model '{model_name}'. Check the model/device settings and available memory. "
                "The first use may need an internet connection to download model weights. Audio was not sent to Gemini."
            ) from exc


def transcribe_audio_sources(
    audio_paths: Sequence[Path | str],
    *,
    model_name: str = WHISPER_MODEL,
    device: str = WHISPER_DEVICE,
    compute_type: str = WHISPER_COMPUTE_TYPE,
    progress_callback: Optional[Callable[[str, int], None]] = None,
    cancellation_check: Optional[Callable[[], None]] = None,
    model_factory: Optional[Callable[..., Any]] = None,
) -> list[SourceTranscript]:
    """Transcribe files in given order; consume faster-whisper's lazy generator."""
    if not audio_paths:
        raise ValueError("At least one lecture recording is required.")
    model = _get_model(model_name, device, compute_type, model_factory)
    results = []
    count = len(audio_paths)
    for index, raw_path in enumerate(audio_paths, 1):
        path = Path(raw_path)
        if not path.exists() or not path.is_file():
            raise ValueError(f"Recording {index} could not be found.")
        if path.stat().st_size == 0:
            raise ValueError(f"Recording {index} is empty.")
        if progress_callback:
            progress_callback(f"Transcribing recording {index}/{count} locally with faster-whisper...", 20 + int(25 * (index - 1) / count))
        try:
            segments_iter, info = model.transcribe(str(path), language=None)
            segments = []
            for seg in segments_iter:
                if cancellation_check:
                    cancellation_check()
                segments.append(TranscriptSegment(float(seg.start), float(seg.end), str(seg.text).strip()))
        except TypeError as exc:
            if "metadata_errors" in str(exc):
                raise RuntimeError("The installed PyAV version is incompatible with faster-whisper. Reinstall dependencies with: pip install -r requirements.txt") from exc
            logger.warning("Local transcription failed for recording %s (%s).", index, type(exc).__name__)
            raise ValueError(f"Recording {index} could not be decoded or transcribed. Check that it is a supported, readable audio file.") from exc
        except Exception as exc:
            if cancellation_check:
                cancellation_check()
            logger.warning("Local transcription failed for recording %s (%s).", index, type(exc).__name__)
            raise ValueError(f"Recording {index} could not be decoded or transcribed. Check that it is a supported, readable audio file.") from exc
        text = " ".join(segment.text for segment in segments if segment.text).strip()
        if not text:
            raise ValueError(f"Recording {index} produced an empty transcript. Try another recording or Whisper model size.")
        results.append(SourceTranscript(
            source_index=index,
            text=text,
            segments=segments,
            language=getattr(info, "language", None),
            language_probability=getattr(info, "language_probability", None),
        ))
    return results


def format_transcript(transcripts: Sequence[SourceTranscript]) -> str:
    """Build an ordered, timestamped transcript without exposing local paths."""
    blocks = []
    for source in transcripts:
        language = f"; detected language: {source.language}" if source.language else ""
        if source.language_probability is not None:
            language += f" ({source.language_probability:.2f} confidence)"
        lines = [f"[Recording {source.source_index}{language}]"]
        lines.extend(f"[{segment.start:.2f}-{segment.end:.2f}] {segment.text}" for segment in source.segments if segment.text)
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def transcript_metadata(transcripts: Sequence[SourceTranscript]) -> list[dict[str, Any]]:
    return [asdict(item) for item in transcripts]
