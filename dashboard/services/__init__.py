import sys
from pathlib import Path

# Ensure scripts and dashboard directories are available for service modules
dashboard_path = str(Path(__file__).resolve().parent.parent)
if dashboard_path not in sys.path:
    sys.path.insert(0, dashboard_path)

scripts_path = str(Path(__file__).resolve().parent.parent.parent / "scripts")
if scripts_path not in sys.path:
    sys.path.insert(0, scripts_path)
