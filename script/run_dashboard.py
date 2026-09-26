from __future__ import annotations

import webbrowser
from pathlib import Path
from observability.dashboard import generate_html_dashboard

if __name__ == "__main__":
    path = generate_html_dashboard()
    print(f"\nOpening dashboard in web browser: {path}")
    try:
        webbrowser.open(f"file://{path.resolve()}")
    except Exception:
        pass
