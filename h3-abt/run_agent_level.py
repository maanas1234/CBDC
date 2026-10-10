"""Agent-level re-analysis of the confirmatory run (addresses action-level pseudo-replication)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from h3_abt.agent_level import analyze_csv, to_dict  # noqa: E402

if __name__ == "__main__":
    source = Path(sys.argv[1] if len(sys.argv) > 1 else "results/confirmatory_seed42.csv")
    target = source.with_name(source.stem.replace("confirmatory", "agent_level") + ".json")
    result = to_dict(analyze_csv(source))
    target.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"wrote {target}")
