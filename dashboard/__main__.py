"""Development entrypoint: ``python -m dashboard``.

``python -m package`` executes ``package/__main__.py``, not ``__init__.py``,
so this module exists to keep that invocation working after the legacy
``dashboard/app.py`` monolith was removed.
"""
import os

from dashboard import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=True)
