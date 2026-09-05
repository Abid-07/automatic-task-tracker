"""Main application entry point for Automatic Task Tracker."""

import argparse
import time
from dotenv import load_dotenv

load_dotenv()

from screenshot import capture_full_screen
from vision_summarizer import IntervalSummarizer
from clean_screenshots import delete_all_screenshots


def _build_summarizer(summary_mode: str, summary_interval_minutes: float, enable_summary: bool) -> IntervalSummarizer:
    """Construct an IntervalSummarizer based on the chosen summary mode.

    - "hourly": wall-clock aligned to the top of every hour (2:00 PM, 3:00 PM, ...).
    - "HH":     wall-clock aligned to every half hour (2:00 PM, 2:30 PM, 3:00 PM, ...).
    - "fixed":  fixed-duration interval starting from the first screenshot (uses --interval-minutes).
    """
    if summary_mode in ("hourly", "HH"):
        return IntervalSummarizer(enable_summary=enable_summary, mode=summary_mode)
    return IntervalSummarizer(interval_minutes=summary_interval_minutes, enable_summary=enable_summary)


def run_periodic(interval_seconds: float, summary_interval_minutes: float, summary_mode: str, enable_summary: bool = True) -> None:
    """Periodically capture screenshots every `interval_seconds` and generate 1-2 line summaries per the summary mode."""
    summarizer = _build_summarizer(summary_mode, summary_interval_minutes, enable_summary)

    print(f"Starting periodic screenshots every {interval_seconds}s.")
    if summary_mode in ("hourly", "HH"):
        label = "top of every hour (e.g. 2:00, 3:00)" if summary_mode == "hourly" else "every half hour (e.g. 2:00, 2:30, 3:00)"
        print(f"Summary mode: {summary_mode} -> summaries generated at {label}.")
    else:
        print(f"Summary generated every {summary_interval_minutes} minute(s).")
    print("Press Ctrl+C to stop.\n")

    try:
        while True:
            filepath, ts = capture_full_screen()
            print(f"[{ts.strftime('%Y-%m-%d %H:%M:%S')}] Captured screenshot: {filepath}")

            summarizer.add_screenshot(filepath, ts)
            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        print("\nStopping periodic screenshot capture...")
    finally:
        summarizer.flush_summary()
        _cleanup_session()


def run_manual(summary_interval_minutes: float, summary_mode: str, enable_summary: bool = True) -> None:
    """Wait for terminal input (Enter) to capture screenshots and generate summaries per the summary mode."""
    summarizer = _build_summarizer(summary_mode, summary_interval_minutes, enable_summary)

    print("Manual screenshot mode ready.")
    if summary_mode in ("hourly", "HH"):
        label = "top of every hour (e.g. 2:00, 3:00)" if summary_mode == "hourly" else "every half hour (e.g. 2:00, 2:30, 3:00)"
        print(f"Summary mode: {summary_mode} -> summaries generated at {label}.")
    else:
        print(f"Summary interval: every {summary_interval_minutes} minute(s).")
    print("Press Enter to take a screenshot, 's' to force a summary, or 'q' / 'exit' to quit.\n")

    while True:
        try:
            user_input = input("Press Enter to capture ('s' for summary, 'q' to quit): ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting manual mode...")
            break

        if user_input in ("q", "quit", "exit"):
            print("Exiting manual screenshot mode...")
            break

        if user_input == "s":
            summarizer.flush_summary()
            continue

        filepath, ts = capture_full_screen()
        print(f"[{ts.strftime('%Y-%m-%d %H:%M:%S')}] Captured screenshot: {filepath}")
        summarizer.add_screenshot(filepath, ts)

    summarizer.flush_summary()
    _cleanup_session()


def _cleanup_session() -> None:
    """Delete all screenshots captured during the session to avoid disk clutter."""
    print("\nCleaning up session screenshots...")
    count = delete_all_screenshots()
    print(f"Deleted {count} screenshot file(s). Session complete.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Automatic Task Tracker Screenshot & Vision Utility")
    parser.add_argument(
        "-p", "--periodic",
        type=float,
        nargs="?",
        const=5.0,
        metavar="SECONDS",
        help="Take screenshots periodically every SECONDS (default: 5.0). If omitted, runs in manual input mode."
    )
    parser.add_argument(
        "-i", "--interval-minutes",
        type=float,
        default=30.0,
        metavar="MINUTES",
        help="Fixed-duration interval in minutes to summarize screenshots (default: 30.0). Ignored if --summary-mode is 'hourly' or 'HH'."
    )
    parser.add_argument(
        "-m", "--summary-mode",
        choices=["fixed", "hourly", "HH"],
        default="fixed",
        help="Summary timing mode: 'hourly' aligns summaries to the top of each hour (2 PM, 3 PM); "
             "'HH' aligns summaries to every half hour (2 PM, 2:30 PM, 3 PM); "
             "'fixed' uses a rolling --interval-minutes duration (default)."
    )
    parser.add_argument(
        "--no-summary",
        action="store_true",
        help="Disable Vision API AI summaries."
    )
    args = parser.parse_args()

    enable_summary = not args.no_summary

    if args.periodic is not None:
        run_periodic(
            interval_seconds=args.periodic,
            summary_interval_minutes=args.interval_minutes,
            summary_mode=args.summary_mode,
            enable_summary=enable_summary,
        )
    else:
        run_manual(
            summary_interval_minutes=args.interval_minutes,
            summary_mode=args.summary_mode,
            enable_summary=enable_summary,
        )


if __name__ == "__main__":
    main()

