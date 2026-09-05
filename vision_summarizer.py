"""Vision API module using Google Gemini to summarize desktop screenshots."""

import os
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from PIL import Image

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from google import genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False


def get_gemini_client() -> Optional["genai.Client"]:
    """Initialize and return Google Gemini client if API key is available."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    if not HAS_GENAI:
        return None
    return genai.Client(api_key=api_key)


def summarize_batch(
    image_paths: List[str],
    interval_label: str = "",
    prompt: Optional[str] = None,
    model_name: Optional[str] = None,
) -> str:
    """Summarize a collection of screenshots taken during a time interval into a single 1-2 line summary.

    The prompt instructs the model to focus on the dominant, sustained activity across
    the batch and to ignore brief one-off distractions (e.g. checking a stock app or a
    video for a screenshot or two) that don't represent the main focus of the interval.
    """
    if not image_paths:
        return "No screenshots taken during this interval."

    client = get_gemini_client()
    if not client:
        if not os.environ.get("GEMINI_API_KEY"):
            return f"[GEMINI_API_KEY not set] {len(image_paths)} screenshot(s) captured during {interval_label}. Set GEMINI_API_KEY environment variable to enable Vision AI summaries."
        return f"[google-genai error] {len(image_paths)} screenshot(s) captured during {interval_label}."

    models_to_try = [model_name] if model_name else ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-flash-latest"]
    env_model = os.environ.get("GEMINI_MODEL")
    if env_model and env_model not in models_to_try:
        models_to_try.insert(0, env_model)

    # Sample evenly across the whole interval (rather than just the first N) so the
    # dominant activity is represented fairly even if the interval has many screenshots.
    sampled_paths = _sample_evenly(image_paths, max_count=10)

    images = []
    for path in sampled_paths:
        if os.path.exists(path):
            images.append(Image.open(path))

    if not images:
        return "No valid screenshot image files found to analyze."

    if prompt is None:
        prompt = (
            "You are given a sequence of desktop screenshots captured periodically during a single work interval, "
            "in chronological order. Identify the ONE dominant, sustained activity or task that the user spent "
            "most of the interval doing (e.g. writing a document, coding, reading email). "
            "Ignore brief, incidental distractions that only appear in one or two screenshots and are not "
            "representative of the overall interval (e.g. a quick glance at a stock ticker, a video, or a chat "
            "notification amid mostly document-writing). Do not mention these minor outliers in your summary. "
            "Write a concise 1-2 sentence summary describing only the main, sustained activity of this interval."
        )

    contents = images + [f"{prompt}\nInterval: {interval_label}"]

    last_error = None
    for target_model in models_to_try:
        try:
            response = client.models.generate_content(
                model=target_model,
                contents=contents,
            )
            return response.text.strip()
        except Exception as e:
            last_error = e
            if "404" in str(e) or "NOT_FOUND" in str(e):
                continue
            break

    return f"[Error generating batch summary for {interval_label}: {last_error}]"


def _sample_evenly(items: List[str], max_count: int) -> List[str]:
    """Return up to `max_count` items evenly spaced across the list, preserving order.

    This avoids biasing the summary toward only the earliest screenshots when an
    interval contains more images than the API payload cap.
    """
    if len(items) <= max_count:
        return items
    step = len(items) / max_count
    indices = sorted({int(i * step) for i in range(max_count)})
    return [items[i] for i in indices]


class IntervalSummarizer:
    """Manages screenshot collections over wall-clock-aligned time intervals and generates summaries.

    Supports two alignment modes:
      - "hourly": summaries trigger at the top of every hour (e.g. 2:00 PM, 3:00 PM).
      - "HH":     summaries trigger every half hour (e.g. 2:00 PM, 2:30 PM, 3:00 PM).

    Falls back to a fixed-duration (non-wall-clock-aligned) interval when mode=None.
    """

    def __init__(
        self,
        interval_minutes: float = 30.0,
        enable_summary: bool = True,
        log_file: str = "activity_summary.log",
        mode: Optional[str] = None,
    ):
        self.interval_minutes = interval_minutes
        self.enable_summary = enable_summary
        self.log_file = log_file
        self.mode = mode  # None, "hourly", or "HH"
        self.current_batch: List[Tuple[str, datetime]] = []
        self.interval_start: Optional[datetime] = None
        self.next_boundary: Optional[datetime] = None

        if self.mode == "hourly":
            self.boundary_minutes = 60
        elif self.mode == "HH":
            self.boundary_minutes = 30
        else:
            self.boundary_minutes = None

    def _compute_next_boundary(self, after: datetime) -> datetime:
        """Compute the next wall-clock boundary (e.g. next :00 or next :00/:30) after `after`."""
        step = self.boundary_minutes
        base = after.replace(second=0, microsecond=0)
        # Round down to the nearest step, then advance to the next boundary.
        minutes_since_hour_start = base.minute - (base.minute % step)
        boundary = base.replace(minute=minutes_since_hour_start)
        while boundary <= after:
            boundary += timedelta(minutes=step)
        return boundary

    def add_screenshot(self, filepath: str, timestamp: datetime) -> Optional[str]:
        """Add a screenshot to the current interval batch.

        If the interval/boundary has elapsed, triggers and returns the interval summary.
        """
        if self.interval_start is None:
            self.interval_start = timestamp
            if self.boundary_minutes is not None:
                self.next_boundary = self._compute_next_boundary(timestamp)

        self.current_batch.append((filepath, timestamp))

        if self.boundary_minutes is not None:
            # Wall-clock aligned mode (hourly / HH): flush when we cross the next boundary.
            if self.next_boundary is not None and timestamp >= self.next_boundary:
                return self.flush_summary(current_time=timestamp)
        else:
            # Fixed-duration mode: flush after interval_minutes have elapsed.
            elapsed_seconds = (timestamp - self.interval_start).total_seconds()
            if elapsed_seconds >= self.interval_minutes * 60:
                return self.flush_summary(current_time=timestamp)

        return None

    def flush_summary(self, current_time: Optional[datetime] = None) -> str:
        """Force flush accumulated screenshots and generate a 1-2 line summary."""
        if not self.current_batch:
            return "No screenshots captured in interval."

        if current_time is None:
            current_time = datetime.now()

        start_str = self.interval_start.strftime("%H:%M") if self.interval_start else ""
        end_str = current_time.strftime("%H:%M")
        interval_label = f"{start_str} - {end_str}"

        image_paths = [path for path, _ in self.current_batch]

        if self.enable_summary:
            summary = summarize_batch(image_paths, interval_label=interval_label)
        else:
            summary = f"Summary disabled. Captured {len(image_paths)} screenshot(s) during {interval_label}."

        log_entry = f"[{datetime.now().strftime('%Y-%m-%d')} | {interval_label}] ({len(image_paths)} screenshots)\nSummary: {summary}\n"

        print(f"\n==================== INTERVAL SUMMARY ({interval_label}) ====================")
        print(f"Screenshots in batch: {len(image_paths)}")
        print(f"Summary: {summary}")
        print(f"========================================================================\n")

        # Save summary to log file
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_entry + "\n")
            print(f"Saved summary entry to {self.log_file}\n")
        except Exception as e:
            print(f"Error saving to log file {self.log_file}: {e}")

        # Reset batch state for next interval
        self.current_batch = []
        self.interval_start = current_time
        if self.boundary_minutes is not None:
            self.next_boundary = self._compute_next_boundary(current_time)

        return summary
