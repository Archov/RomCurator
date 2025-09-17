from pathlib import Path

path = Path("scripts/seeders/matching_engine.py")
lines = path.read_text().splitlines()
for idx, line in enumerate(lines):
    if line.strip() == "if not linked_platform_ids:" and lines[idx-1].strip().startswith("logger.debug"):
        # remove this redundant block (lines idx, idx+1 maybe blank after) but ensure next line is 'continue'
        lines.pop(idx)  # remove if line
        if lines[idx].strip() == "continue":
            lines.pop(idx)
        break
path.write_text("\n".join(lines) + "\n")
