#!/usr/bin/env python3
"""Generate a structured changelog by diffing the current branch against a base ref.

Detects mod version changes (manifest.json, server-mods.json) and config value
changes across BepInEx .cfg, YAML, and JSON files in Config/.

Usage:
    python3 scripts/generate-changelog.py --base main
    python3 scripts/generate-changelog.py --base origin/main --output changelog.md
"""

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field

try:
    import yaml
except ImportError:
    yaml = None

# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

def git_show(ref: str, path: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "show", f"{ref}:{path}"],
            capture_output=True, text=True, check=True,
        )
        return result.stdout
    except subprocess.CalledProcessError:
        return None


def git_diff_names(base: str) -> list[tuple[str, str]]:
    result = subprocess.run(
        ["git", "diff", "--name-status", f"{base}...HEAD"],
        capture_output=True, text=True, check=True,
    )
    entries = []
    for line in result.stdout.strip().splitlines():
        parts = line.split("\t", 1)
        if len(parts) == 2:
            entries.append((parts[0][0], parts[1]))  # (status_char, path)
    return entries


def read_file(path: str) -> str | None:
    try:
        with open(path) as f:
            return f.read()
    except FileNotFoundError:
        return None


# ---------------------------------------------------------------------------
# Mod dependency parsing
# ---------------------------------------------------------------------------

def parse_mod_string(s: str) -> tuple[str, str, str]:
    """Parse 'Namespace-Name-1.2.3' into (namespace, name, version)."""
    parts = s.rsplit("-", 2)
    if len(parts) == 3:
        return parts[0], parts[1], parts[2]
    # Fallback for unexpected formats
    return s, "", ""


def parse_deps_file(content: str | None) -> dict[str, str]:
    """Parse a JSON file with a 'dependencies' array. Returns {namespace-name: version}."""
    if not content:
        return {}
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return {}
    deps = {}
    for dep_str in data.get("dependencies", []):
        ns, name, version = parse_mod_string(dep_str)
        key = f"{ns}-{name}"
        deps[key] = version
    return deps


@dataclass
class ModChanges:
    added: list[tuple[str, str, str]] = field(default_factory=list)  # (display, version, source)
    removed: list[tuple[str, str]] = field(default_factory=list)      # (display, source)
    updated: list[tuple[str, str, str, str]] = field(default_factory=list)  # (display, old, new, source)


def diff_mods(base: str) -> ModChanges:
    changes = ModChanges()
    for path, source in [("manifest.json", "Client"), ("server-mods.json", "Server")]:
        old_deps = parse_deps_file(git_show(base, path))
        new_deps = parse_deps_file(read_file(path))

        for key, version in new_deps.items():
            if key not in old_deps:
                changes.added.append((key, version, source))
            elif old_deps[key] != version:
                changes.updated.append((key, old_deps[key], version, source))

        for key in old_deps:
            if key not in new_deps:
                changes.removed.append((key, source))

    return changes


# ---------------------------------------------------------------------------
# BepInEx .cfg parser
# ---------------------------------------------------------------------------

def parse_cfg(content: str) -> dict[str, dict[str, str]]:
    """Parse BepInEx .cfg into {section: {key: value}}."""
    sections: dict[str, dict[str, str]] = {}
    current_section = "_global"
    sections[current_section] = {}

    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            current_section = stripped[1:-1]
            if current_section not in sections:
                sections[current_section] = {}
            continue
        if "=" in stripped:
            key, _, value = stripped.partition("=")
            sections[current_section][key.strip()] = value.strip()

    return sections


def diff_cfg(old: dict[str, dict[str, str]], new: dict[str, dict[str, str]]) -> list[tuple[str, str, str | None, str | None, str]]:
    """Diff two parsed .cfg structures. Returns [(section, key, old_val, new_val, change_type)]."""
    changes = []
    all_sections = set(old.keys()) | set(new.keys())

    for section in sorted(all_sections):
        old_keys = old.get(section, {})
        new_keys = new.get(section, {})
        all_keys = set(old_keys.keys()) | set(new_keys.keys())

        for key in sorted(all_keys):
            old_val = old_keys.get(key)
            new_val = new_keys.get(key)
            if old_val == new_val:
                continue
            if old_val is None:
                changes.append((section, key, None, new_val, "added"))
            elif new_val is None:
                changes.append((section, key, old_val, None, "removed"))
            else:
                changes.append((section, key, old_val, new_val, "modified"))

    return changes


# ---------------------------------------------------------------------------
# YAML / JSON parsers
# ---------------------------------------------------------------------------

def parse_yaml(content: str) -> dict | list | None:
    if yaml is None:
        return None
    try:
        return yaml.safe_load(content)
    except yaml.YAMLError:
        return None


def parse_json(content: str) -> dict | list | None:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return None


# ---------------------------------------------------------------------------
# Structural diff for nested dicts/lists
# ---------------------------------------------------------------------------

def flatten(obj, prefix: str = "") -> dict[str, str]:
    """Flatten a nested structure into {dotted.path: str(value)}."""
    result = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            path = f"{prefix}.{k}" if prefix else str(k)
            if isinstance(v, (dict, list)):
                result.update(flatten(v, path))
            else:
                result[path] = str(v)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            path = f"{prefix}[{i}]"
            if isinstance(item, (dict, list)):
                result.update(flatten(item, path))
            else:
                result[path] = str(item)
    else:
        result[prefix] = str(obj)
    return result


def diff_trader_list(old_list: list, new_list: list) -> list[tuple[str, str | None, str | None, str]]:
    """Diff trader JSON arrays matched by 'prefab' field."""
    changes = []
    old_by_prefab = {item.get("prefab", f"_idx{i}"): item for i, item in enumerate(old_list)}
    new_by_prefab = {item.get("prefab", f"_idx{i}"): item for i, item in enumerate(new_list)}

    for prefab, item in new_by_prefab.items():
        if prefab not in old_by_prefab:
            desc = ", ".join(f"{k}: {v}" for k, v in item.items() if k != "prefab")
            changes.append((f"Added item: {prefab}", None, desc, "added"))
        else:
            old_item = old_by_prefab[prefab]
            for k in set(old_item.keys()) | set(item.keys()):
                if k == "prefab":
                    continue
                ov = old_item.get(k)
                nv = item.get(k)
                if ov != nv:
                    changes.append((f"{prefab}.{k}", str(ov), str(nv), "modified"))

    for prefab in old_by_prefab:
        if prefab not in new_by_prefab:
            changes.append((f"Removed item: {prefab}", None, None, "removed"))

    return changes


def diff_flat(old: dict | list | None, new: dict | list | None) -> list[tuple[str, str | None, str | None, str]]:
    """Generic structural diff via flattening."""
    old_flat = flatten(old) if old else {}
    new_flat = flatten(new) if new else {}
    changes = []
    all_keys = set(old_flat.keys()) | set(new_flat.keys())

    for key in sorted(all_keys):
        ov = old_flat.get(key)
        nv = new_flat.get(key)
        if ov == nv:
            continue
        if ov is None:
            changes.append((key, None, nv, "added"))
        elif nv is None:
            changes.append((key, ov, None, "removed"))
        else:
            changes.append((key, ov, nv, "modified"))

    return changes


# ---------------------------------------------------------------------------
# Markdown formatting
# ---------------------------------------------------------------------------

BINARY_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".dat", ".bin", ".dll"}
MAX_VALUE_LEN = 100
MAX_FILE_CHARS = 5000
MAX_TOTAL_CHARS = 58000


def truncate(val: str | None) -> str:
    if val is None:
        return ""
    if len(val) > MAX_VALUE_LEN:
        return val[:MAX_VALUE_LEN] + "..."
    return val


def format_mod_changes(mod_changes: ModChanges) -> str:
    if not mod_changes.added and not mod_changes.removed and not mod_changes.updated:
        return ""

    lines = ["## Mod Changes\n"]

    for source in ["Client", "Server"]:
        added = [(d, v) for d, v, s in mod_changes.added if s == source]
        removed = [d for d, s in mod_changes.removed if s == source]
        updated = [(d, o, n) for d, o, n, s in mod_changes.updated if s == source]

        if not added and not removed and not updated:
            continue

        lines.append(f"### {source} Mods\n")
        for display, version in sorted(added):
            lines.append(f"- **Added:** {display} {version}")
        for display, old_v, new_v in sorted(updated):
            lines.append(f"- **Updated:** {display} {old_v} → {new_v}")
        for display in sorted(removed):
            lines.append(f"- **Removed:** {display}")
        lines.append("")

    return "\n".join(lines)


def format_cfg_changes(path: str, changes: list) -> str:
    lines = [f"### {path}\n"]
    char_count = 0

    for section, key, old_val, new_val, change_type in changes:
        if change_type == "added":
            line = f"- **[{section}]** {key}: `{truncate(new_val)}` *(added)*"
        elif change_type == "removed":
            line = f"- **[{section}]** {key}: ~~`{truncate(old_val)}`~~ *(removed)*"
        else:
            line = f"- **[{section}]** {key}: `{truncate(old_val)}` → `{truncate(new_val)}`"

        char_count += len(line)
        if char_count > MAX_FILE_CHARS:
            remaining = len(changes) - len(lines) + 1
            lines.append(f"\n<details><summary>... and {remaining} more changes</summary>\n")
            lines.append(line)
            # Continue adding inside details
            for s, k, ov, nv, ct in changes[len(lines) - 2:]:
                if ct == "modified":
                    lines.append(f"- **[{s}]** {k}: `{truncate(ov)}` → `{truncate(nv)}`")
                elif ct == "added":
                    lines.append(f"- **[{s}]** {k}: `{truncate(nv)}` *(added)*")
                elif ct == "removed":
                    lines.append(f"- **[{s}]** {k}: ~~`{truncate(ov)}`~~ *(removed)*")
            lines.append("</details>")
            break
        lines.append(line)

    lines.append("")
    return "\n".join(lines)


def format_generic_changes(path: str, changes: list, label: str = "") -> str:
    lines = [f"### {path}\n"]
    char_count = 0
    overflow = 0

    for key, old_val, new_val, change_type in changes:
        if change_type == "added" and old_val is None:
            line = f"- **{key}**: `{truncate(new_val)}`"
        elif change_type == "removed":
            line = f"- **{key}** *(removed)*"
        else:
            line = f"- **{key}**: `{truncate(old_val)}` → `{truncate(new_val)}`"

        char_count += len(line)
        if char_count > MAX_FILE_CHARS:
            overflow += 1
            continue
        lines.append(line)

    if overflow:
        lines.append(f"- ... and {overflow} more changes")

    lines.append("")
    return "\n".join(lines)


def generate_changelog(base: str) -> str:
    # --- Mod changes ---
    mod_changes = diff_mods(base)
    mod_section = format_mod_changes(mod_changes)

    # --- Config changes ---
    diff_entries = git_diff_names(base)
    config_sections = []
    total_chars = len(mod_section)

    for status, filepath in sorted(diff_entries, key=lambda x: x[1]):
        # Only process Config/ files
        if not filepath.startswith("Config/"):
            continue

        display_path = filepath[len("Config/"):]  # Strip Config/ prefix for display
        ext = os.path.splitext(filepath)[1].lower()

        # Binary files
        if ext in BINARY_EXTS:
            if status == "A":
                config_sections.append(f"### {display_path}\n- Binary file added\n")
            elif status == "D":
                config_sections.append(f"### {display_path}\n- Binary file removed\n")
            else:
                config_sections.append(f"### {display_path}\n- Binary file changed\n")
            continue

        # Get old and new content
        old_content = git_show(base, filepath) if status != "A" else None
        new_content = read_file(filepath) if status != "D" else None

        # Deleted file
        if new_content is None:
            config_sections.append(f"### {display_path}\n- *(file deleted)*\n")
            continue

        # New file
        if old_content is None:
            config_sections.append(f"### {display_path}\n- *(new file)*\n")
            continue

        # Parse and diff based on format
        section_text = ""

        if ext == ".cfg":
            old_parsed = parse_cfg(old_content)
            new_parsed = parse_cfg(new_content)
            changes = diff_cfg(old_parsed, new_parsed)
            if changes:
                section_text = format_cfg_changes(display_path, changes)

        elif ext in (".yml", ".yaml"):
            if yaml is None:
                if old_content != new_content:
                    section_text = f"### {display_path}\n- File modified *(install pyyaml for detailed diff)*\n"
            else:
                old_parsed = parse_yaml(old_content)
                new_parsed = parse_yaml(new_content)
                if old_parsed is None or new_parsed is None:
                    if old_content != new_content:
                        section_text = f"### {display_path}\n- File modified *(parse error)*\n"
                else:
                    changes = diff_flat(old_parsed, new_parsed)
                    if changes:
                        section_text = format_generic_changes(display_path, changes)

        elif ext == ".json":
            old_parsed = parse_json(old_content)
            new_parsed = parse_json(new_content)
            if old_parsed is None or new_parsed is None:
                if old_content != new_content:
                    section_text = f"### {display_path}\n- File modified *(parse error)*\n"
            else:
                # Detect trader lists (root is array with 'prefab' keys)
                if (isinstance(old_parsed, list) and isinstance(new_parsed, list)
                        and old_parsed and isinstance(old_parsed[0], dict)
                        and "prefab" in old_parsed[0]):
                    changes = diff_trader_list(old_parsed, new_parsed)
                else:
                    changes = diff_flat(old_parsed, new_parsed)
                if changes:
                    section_text = format_generic_changes(display_path, changes)

        else:
            if old_content != new_content:
                section_text = f"### {display_path}\n- File modified\n"

        if section_text:
            total_chars += len(section_text)
            if total_chars > MAX_TOTAL_CHARS:
                config_sections.append(f"\n*... changelog truncated ({len(diff_entries)} files total)*\n")
                break
            config_sections.append(section_text)

    # --- Assemble ---
    parts = ["# Changelog\n"]

    if not mod_section and not config_sections:
        parts.append("No gameplay changes detected in this PR.\n")
        return "\n".join(parts)

    if mod_section:
        parts.append(mod_section)

    if config_sections:
        parts.append("## Config Changes\n")
        parts.extend(config_sections)

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate a changelog from git diff")
    parser.add_argument("--base", default="main", help="Base ref to diff against (default: main)")
    parser.add_argument("--output", help="Write to file instead of stdout")
    args = parser.parse_args()

    changelog = generate_changelog(args.base)

    if args.output:
        with open(args.output, "w") as f:
            f.write(changelog)
        print(f"Changelog written to {args.output}", file=sys.stderr)
    else:
        print(changelog)


if __name__ == "__main__":
    main()
