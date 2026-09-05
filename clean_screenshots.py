"""Ad hoc script to delete all generated screenshot PNG files."""

import glob
import os

from screenshot import DEFAULT_SCREENSHOT_DIR


def delete_all_screenshots(directory: str = DEFAULT_SCREENSHOT_DIR) -> int:
    """Find and delete all PNG screenshot files in directory. Returns count deleted."""
    patterns = [
        os.path.join(directory, "screenshot_*.png"),
        os.path.join(directory, "region.png"),
        os.path.join(directory, "screenshot.png"),
        # Also clean up any legacy screenshots left in the project root from before
        # screenshots were moved into their own folder.
        "screenshot_*.png",
        "region.png",
        "screenshot.png",
    ]

    deleted_count = 0
    seen = set()
    for pattern in patterns:
        for filepath in glob.glob(pattern):
            real_path = os.path.abspath(filepath)
            if real_path in seen:
                continue
            seen.add(real_path)
            try:
                os.remove(filepath)
                print(f"Deleted: {filepath}")
                deleted_count += 1
            except Exception as e:
                print(f"Error deleting {filepath}: {e}")

    return deleted_count


if __name__ == "__main__":
    count = delete_all_screenshots()
    print(f"\nDone! Deleted {count} screenshot file(s).")
