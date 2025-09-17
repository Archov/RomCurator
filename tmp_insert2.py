from pathlib import Path

path = Path("scripts/seeders/matching_engine.py")
lines = path.read_text().splitlines()
for idx, line in enumerate(lines):
    if line.strip() == "linked_platform_ids = self.get_linked_platform_ids(platform_id)":
        insert_idx = idx + 1
        break
else:
    raise SystemExit('linked line not found')
block = [
    "            linked_platform_ids = self.get_linked_platform_ids(platform_id)",
    "            if not linked_platform_ids:",
    "                logger.debug(\"No platform links for atomic %s (%s) on platform %s (%s); skipping\", atomic_title, atomic_id, platform_name, platform_id)",
    "                continue",
    "            logger.debug(\"Atomic %s (%s) platform %s (%s) -> %d linked DAT platforms\", atomic_title, atomic_id, platform_name, platform_id, len(linked_platform_ids))"
]
# Replace the existing line with block (assuming no guard yet)
lines[idx] = block[0]
lines.insert(idx+1, block[1])
lines.insert(idx+2, block[2])
lines.insert(idx+3, block[3])
lines.insert(idx+4, block[4])
path.write_text("\n".join(lines) + "\n")
