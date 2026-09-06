"""Replay the saved live-agent products; does not simulate or resample an agent."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent

with tempfile.TemporaryDirectory(prefix="sop-evaluation-replay-") as temporary:
    for variant in ("unimplemented", "old", "new"):
        repo = Path(temporary) / variant
        shutil.copytree(ROOT / "evaluation_fixture", repo)
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        if variant != "unimplemented":
            subprocess.run(["git", "-C", str(repo), "apply", str(ROOT / "evaluation-results" / (variant + ".patch"))], check=True)
        result = subprocess.run([sys.executable, "-B", str(ROOT / "evaluate_product.py"), str(repo)],
                                capture_output=True, text=True)
        expected = 1 if variant == "unimplemented" else 0
        if result.returncode != expected:
            raise SystemExit(f"Unexpected {variant} oracle result:\n{result.stderr}")
        print(f"{variant}: {'rejected as expected' if expected else '8 acceptance checks passed'}")
