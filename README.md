# automatic-task-tracker

Captures desktop screenshots and uses Gemini vision API to summarize activity per interval.

## Setup

```
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Add to `.env`: `GEMINI_API_KEY=your_api_key_here`

## Commands

```
python main.py                                # manual mode, Enter = capture, s = summary, q = quit
python main.py -p 30 -i 20                    # screenshot every 30s, summary every 20min (fixed)
python main.py -p 30 -m hourly                # summary aligned to top of each hour
python main.py -p 30 -m HH                    # summary aligned to every half hour
python main.py -p 30 -m hourly --no-summary   # skip Gemini API, just track counts
python screenshot.py                          # take a single screenshot
python clean_screenshots.py                   # delete all stored screenshots
```

Screenshots are stored in `screenshots/` and deleted automatically at session end.
Summaries are appended to `activity_summary.log`.
