"""Example usage of the `mss` library for taking screenshots."""

import os
from datetime import datetime
from typing import Optional, Tuple
import mss
import mss.tools

DEFAULT_SCREENSHOT_DIR = "screenshots"


def capture_full_screen(output_path: Optional[str] = None, output_dir: str = DEFAULT_SCREENSHOT_DIR) -> Tuple[str, datetime]:
    """Capture the entire (primary) screen, save it, and return (filepath, timestamp).

    Screenshots are stored inside `output_dir` (created if missing) to avoid
    cluttering the project root. If output_path is None, automatically
    generates a timestamped filename such as 'screenshot_20260905_143040.png'.
    """
    timestamp = datetime.now()
    os.makedirs(output_dir, exist_ok=True)

    if output_path is None:
        filename_ts = timestamp.strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(output_dir, f"screenshot_{filename_ts}.png")

    with mss.MSS() as sct:
        monitor = sct.monitors[1]  # index 0 is "all monitors combined"
        screenshot = sct.grab(monitor)
        mss.tools.to_png(screenshot.rgb, screenshot.size, output=output_path)

    return output_path, timestamp


if __name__ == "__main__":
    filepath, ts = capture_full_screen()
    print(f"Saved screenshot to {filepath} at {ts.strftime('%Y-%m-%d %H:%M:%S')}")
