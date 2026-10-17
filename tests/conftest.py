import sys
from pathlib import Path

# The scripts live in the repository root, not in a package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
