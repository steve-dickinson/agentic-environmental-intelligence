import sys
from pathlib import Path

src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from defra_agent.agent.main import run_once  # noqa: E402

if __name__ == "__main__":
    run_once()
