# -*- coding: utf-8 -*-
"""Application entrypoint for Gunicorn (`dashboard.app:app`) and direct execution."""
import os

from dashboard import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    # nosec B104 - 0.0.0.0 is required to bind from outside a container.
    app.run(host="0.0.0.0", port=port, debug=False)  # nosec B104
