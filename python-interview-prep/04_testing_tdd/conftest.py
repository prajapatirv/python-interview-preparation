import sys
from pathlib import Path

# Make `src` importable as `from src.order_service import ...` regardless of where pytest is
# invoked from.
sys.path.insert(0, str(Path(__file__).parent))
