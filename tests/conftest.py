import sys
from pathlib import Path

# Add the repository root so imports like ``src.lazyshell`` resolve correctly
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
