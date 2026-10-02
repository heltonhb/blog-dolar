# -*- coding: utf-8 -*-
"""WSGI entrypoint for production (Render / Gunicorn)."""
import os

from dashboard import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    # nosec B104 - 0.0.0.0 is required to bind from outside a container.
    # Production is served by gunicorn (`gunicorn wsgi:app`), not this.
    app.run(host="0.0.0.0", port=port, debug=False)  # nosec B104
