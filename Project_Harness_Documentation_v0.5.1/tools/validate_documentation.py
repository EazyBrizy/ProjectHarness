#!/usr/bin/env python3
"""Structural and registry/contract semantic validator for Project Harness documentation v0.5.0."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import zipfile
from typing import Any, Iterable
from urllib.parse import unquote

import yaml

VERSION = "0.5.0"
DATE = "2026-08-18"
VALIDATOR_VERSION = "1.4.0"
FULL_NAME = "Project_Harness_Architecture_v0.5.0_FULL.md"
GUIDE_NAME = "Project_Harness_User_and_Implementation_Guide_v0.5.0.md"
EXPECTED_SPECS = [f"{i:02d}_" for i in range(1, 25)]
GENERATED_NAMES = {
    FULL_NAME,
    GUIDE_NAME,
    "FILE_INDEX.md",
    "VALIDATION_REPORT.md",
}
LEGACY_ALLOWED_NAMES = {
    "CHANGELOG.md",
    "MIGRATION_FROM_v0.1.0.md",
    "MIGRATION_FROM_v0.2.0.md",
    "MIGRATION_FROM_v0.3.0.md",
    "MIGRATION_FROM_v0.3.1.md",
    "MIGRATION_FROM_v0.4.0.md",
    "MIGRATION_FROM_v0.4.1.md",
}
SOURCE_DIRS = [
    "00_Overview",
    "01_Architecture",
    "02_Intake",
    "03_Planning",
    "04_Execution",
    "05_Updates",
    "06_Git",
    "07_Security",
    "08_Distribution",
    "09_Delivery",
    "10_Contracts",
    "11_Appendices",
    "12_Implementation_Specifications",
    "registries",
]
LEGACY_ID_PATTERN = re.compile(
    r"\b(?:REQST|DECMP|ACTOR|PDF|CTXP|GRANT|LEASE|PRM|ECP|UPD|AGT|MDL|TOOL)-"
)
ID_PATTERN = re.compile(r"\b([A-Z][A-Z0-9]{1,11})-[A-Z0-9][A-Z0-9._:/-]*")
FALSE_ID_PREFIXES = {"PH", "SHA", "SIDE", "MACHINE", "REGISTRY", "ACTIVE", "BROWNFIELD", "CONTRACT", "UTF"}
MD_LINK_PATTERN = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
ANY_MD_LINK_PATTERN = re.compile(r"(!?\[[^\]]*\]\()([^)]+)(\))")
FENCE_PATTERN = re.compile(r"^\s*(```|~~~)")
FENCE_OPEN_PATTERN = re.compile(r"^\s*(```|~~~)([A-Za-z0-9_-]*)\s*$")
ROADMAP_HEADING_PATTERN = re.compile(r"^### (WP-HARNESS-\d{3}) — (.+?)\s*$")
ROADMAP_TABLE_PATTERN = re.compile(r"^\| `(WP-HARNESS-\d{3})` \| (.+?) \|\s*$")
CAPABILITY_FIELDS = {
    "required_capabilities",
    "requested_capabilities",
    "allowed_capabilities",
    "capabilities",
    "requested_side_effects",
    "prohibited_side_effects",
}
FORBIDDEN_ACCOUNTING_KEYS = {
    "provider_billing",
    "provider_cost",
    "billing_account",
    "token_ledger",
    "token_usage",
    "token_count",
    "input_tokens",
    "output_tokens",
    "cost_estimate",
}


@dataclass(frozen=True)
class FencedBlock:
    language: str
    text: str
    start_line: int
    end_line: int


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def tree_hash(paths: Iterable[Path], root: Path) -> str:
    h = hashlib.sha256()
    for path in sorted(paths, key=lambda p: str(p.relative_to(root))):
        rel = str(path.relative_to(root)).replace(os.sep, "/")
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(path.read_bytes())
        h.update(b"\0")
    return h.hexdigest()


def source_markdown_files(root: Path) -> list[Path]:
    files: list[Path] = []
    preferred = [
        "README.md",
        "VERSION.md",
        "CHANGELOG.md",
        "REQUIREMENTS_COVERAGE.md",
        "MIGRATION_FROM_v0.1.0.md",
        "MIGRATION_FROM_v0.2.0.md",
        "MIGRATION_FROM_v0.3.0.md",
        "MIGRATION_FROM_v0.3.1.md",
        "MIGRATION_FROM_v0.4.0.md",
        "MIGRATION_FROM_v0.4.1.md",
    ]
    for name in preferred:
        path = root / name
        if path.exists():
            files.append(path)
    for dirname in SOURCE_DIRS:
        directory = root / dirname
        if directory.exists():
            files.extend(sorted(directory.glob("*.md")))
    seen: set[Path] = set()
    return [path for path in files if not (path in seen or seen.add(path))]


def semantic_markdown_files(root: Path) -> list[Path]:
    excluded = GENERATED_NAMES | LEGACY_ALLOWED_NAMES
    return [
        path
        for path in source_markdown_files(root)
        if path.name not in excluded
    ]


def implementation_spec_files(root: Path) -> list[Path]:
    directory = root / "12_Implementation_Specifications"
    return sorted(
        path
        for path in directory.glob("[0-9][0-9]_*.md")
        if not path.name.startswith("00_")
    )


def parse_manifest(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    if not path.exists():
        return entries
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            digest, rel = line.split("  ", 1)
        except ValueError:
            continue
        entries[rel] = digest
    return entries


def fenced_blocks(text: str) -> list[FencedBlock]:
    blocks: list[FencedBlock] = []
    current: list[str] = []
    in_fence = False
    marker = ""
    language = ""
    start_line = 0
    for line_no, line in enumerate(text.splitlines(), 1):
        match = FENCE_OPEN_PATTERN.match(line)
        if match:
            if not in_fence:
                in_fence = True
                marker = match.group(1)
                language = match.group(2).lower()
                current = []
                start_line = line_no
            elif match.group(1) == marker:
                blocks.append(
                    FencedBlock(
                        language=language,
                        text="\n".join(current),
                        start_line=start_line,
                        end_line=line_no,
                    )
                )
                in_fence = False
                marker = ""
                language = ""
                current = []
            else:
                current.append(line)
            continue
        if in_fence:
            current.append(line)
    return blocks


def extract_marked_body(text: str, family: str, name: str) -> str | None:
    opening = f"<!-- {family}: {name} -->"
    closing = f"<!-- /{family} -->"
    start = text.find(opening)
    if start < 0:
        return None
    start += len(opening)
    end = text.find(closing, start)
    if end < 0:
        return None
    return text[start:end].strip()


def rewrite_links_for_aggregate(text: str, source: Path, root: Path) -> str:
    root_resolved = root.resolve()

    def replace(match: re.Match[str]) -> str:
        prefix, raw, suffix = match.groups()
        target_expr = raw.strip()
        if not target_expr or target_expr.startswith(
            ("http://", "https://", "mailto:", "#", "data:", "/")
        ):
            return match.group(0)

        target_token = target_expr
        title_suffix = ""
        if " " in target_expr:
            target_token, title_suffix = target_expr.split(" ", 1)
            title_suffix = " " + title_suffix

        wrapped = target_token.startswith("<") and target_token.endswith(">")
        token = target_token[1:-1] if wrapped else target_token
        decoded = unquote(token)
        base, separator, fragment = decoded.partition("#")
        path_part, query_separator, query = base.partition("?")
        if not path_part:
            return match.group(0)

        resolved = (source.parent / path_part).resolve()
        try:
            rel = resolved.relative_to(root_resolved).as_posix()
        except ValueError:
            return match.group(0)

        rebuilt = rel
        if query_separator:
            rebuilt += "?" + query
        if separator:
            rebuilt += "#" + fragment
        if wrapped:
            rebuilt = f"<{rebuilt}>"
        return prefix + rebuilt + title_suffix + suffix

    return ANY_MD_LINK_PATTERN.sub(replace, text)


def shift_headings(text: str, amount: int = 1) -> str:
    output: list[str] = []
    in_fence = False
    marker = ""
    for line in text.splitlines():
        match = FENCE_PATTERN.match(line)
        if match:
            if not in_fence:
                in_fence = True
                marker = match.group(1)
            elif match.group(1) == marker:
                in_fence = False
                marker = ""
            output.append(line)
            continue
        if not in_fence:
            heading = re.match(r"^(#{1,6})(\s+.*)$", line)
            if heading:
                level = min(6, len(heading.group(1)) + amount)
                line = "#" * level + heading.group(2)
        output.append(line)
    return "\n".join(output).rstrip() + "\n"


def full_aggregate_text(root: Path) -> str:
    sources = source_markdown_files(root)
    inventory = "\n".join(
        f"- `{path.relative_to(root).as_posix()}`" for path in sources
    )
    sections: list[str] = []
    for path in sources:
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        text = rewrite_links_for_aggregate(text, path, root)
        text = shift_headings(text, 1)
        sections.append(f"<!-- SOURCE: {rel} -->\n\n{text.rstrip()}\n")
    return (
        "# Project Harness — полная архитектурная документация v0.5.0\n\n"
        "**Документ:** Project Harness  \n"
        f"**Версия:** {VERSION}  \n"
        f"**Дата:** {DATE}  \n"
        "**Статус:** GENERATED FULL DOCUMENT — редактировать тематические источники\n\n"
        "Этот файл объединяет все редактируемые Markdown-источники комплекта. "
        "Machine-readable registries остаются отдельными canonical files и описаны "
        "в `registries/README.md`. Canonical precedence сохраняется у registries, "
        "schemas и отдельных source documents.\n\n"
        "## Source inventory\n\n"
        f"{inventory}\n\n"
        "---\n\n"
        + "\n---\n\n".join(sections)
    ).rstrip() + "\n"


def guide_aggregate_text(root: Path) -> str:
    sources = implementation_spec_files(root)
    inventory = "\n".join(
        f"{index}. `{path.relative_to(root).as_posix()}`"
        for index, path in enumerate(sources, 1)
    )
    sections: list[str] = []
    for path in sources:
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        text = rewrite_links_for_aggregate(text, path, root)
        text = shift_headings(text, 1)
        sections.append(f"<!-- SOURCE: {rel} -->\n\n{text.rstrip()}\n")
    return (
        "# Project Harness — пользовательское и реализационное руководство v0.5.0\n\n"
        "**Документ:** Project Harness  \n"
        f"**Версия:** {VERSION}  \n"
        f"**Дата:** {DATE}  \n"
        "**Статус:** GENERATED IMPLEMENTATION GUIDE — редактировать source specifications\n\n"
        "Руководство воспроизводимо собрано из 24 нормативных implementation specifications. "
        "Source path markers являются частью generation contract.\n\n"
        "## Состав\n\n"
        f"{inventory}\n\n"
        "---\n\n"
        + "\n---\n\n".join(sections)
    ).rstrip() + "\n"


def first_h1(path: Path) -> str:
    if path.suffix.lower() == ".md":
        for line in path.read_text(encoding="utf-8").splitlines():
            match = re.match(r"^#\s+(.+?)\s*$", line)
            if match:
                return match.group(1)
        return "Markdown document"
    if path.suffix.lower() in {".yaml", ".yml"}:
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            reg_id = ((data.get("registry") or {}).get("id")) if isinstance(data, dict) else None
            return f"Machine-readable registry {reg_id}" if reg_id else "Machine-readable YAML"
        except Exception:
            return "Machine-readable YAML"
    if path.suffix.lower() == ".py":
        return "Documentation validation tool"
    return "Distribution artifact"


def file_index_text(root: Path) -> str:
    indexed = sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.name not in {"FILE_INDEX.md", "MANIFEST.sha256"}
    )
    markdown = sum(path.suffix.lower() == ".md" for path in indexed)
    machine_yaml = sum(path.suffix.lower() in {".yaml", ".yml"} for path in indexed)
    tools = sum(path.suffix.lower() == ".py" for path in indexed)
    rows = [
        "| 1 | `MANIFEST.sha256` | SHA-256 manifest, генерируется после всех остальных файлов | — | — |"
    ]
    for index, path in enumerate(indexed, 2):
        rel = path.relative_to(root).as_posix()
        lines = len(path.read_text(encoding="utf-8", errors="replace").splitlines())
        size = path.stat().st_size
        purpose = first_h1(path).replace("|", "/")
        rows.append(
            f"| {index} | [`{rel}`]({rel}) | {purpose} | {lines} | {size} |"
        )
    return (
        "# Индекс файлов Project Harness v0.5.0\n\n"
        "**Документ:** Project Harness  \n"
        f"**Версия:** {VERSION}  \n"
        f"**Дата:** {DATE}  \n"
        "**Статус:** GENERATED FILE INDEX\n\n"
        "## Сводка\n\n"
        f"- индексируемых файлов, кроме этого индекса и manifest: {len(indexed)};\n"
        f"- Markdown: {markdown};\n"
        f"- machine-readable YAML: {machine_yaml};\n"
        f"- tools: {tools}.\n\n"
        "## Полный список\n\n"
        "| № | Файл | Назначение | Строк | Bytes |\n"
        "|---:|---|---|---:|---:|\n"
        + "\n".join(rows)
        + "\n"
    )


def build_aggregates(root: Path) -> None:
    (root / FULL_NAME).write_text(full_aggregate_text(root), encoding="utf-8")
    (root / GUIDE_NAME).write_text(guide_aggregate_text(root), encoding="utf-8")
    (root / "FILE_INDEX.md").write_text(file_index_text(root), encoding="utf-8")


def generated_status_matrix(groups: dict[str, list[str]]) -> str:
    rows = ["| Status group | Допустимые значения |", "|---|---|"]
    for group, values in groups.items():
        rendered = ", ".join(f"`{value}`" for value in values)
        rows.append(f"| `{group}` | {rendered} |")
    return "\n".join(rows)


def generated_request_routing_matrix(registry: dict[str, Any]) -> str:
    lines: list[str] = []
    for group in ("request_classes", "request_modes", "internal_operations"):
        lines.append(f"{group}:")
        lines.extend(f"  - {value}" for value in (registry.get(group) or []))
    return "```yaml\n" + "\n".join(lines) + "\n```"


def generated_capabilities_matrix(entries: list[dict[str, Any]]) -> str:
    values = [str(entry.get("key")) for entry in entries]
    return "```text\n" + "\n".join(values) + "\n```"


def marked_enum_values(text: str, group: str) -> list[str] | None:
    body = extract_marked_body(text, "REGISTRY-ENUM", group)
    if body is None:
        return None
    blocks = fenced_blocks(body)
    if len(blocks) != 1:
        return None
    return [line.strip() for line in blocks[0].text.splitlines() if line.strip()]


def id_prefix(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    match = re.match(r"^([A-Z][A-Z0-9]{1,11})-", value)
    return match.group(1) if match else None


def iter_yaml_examples(paths: Iterable[Path], root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    examples: list[dict[str, Any]] = []
    errors: list[str] = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for block in fenced_blocks(text):
            if block.language not in {"yaml", "yml"}:
                continue
            try:
                value = yaml.safe_load(block.text)
            except Exception as exc:
                errors.append(
                    f"{path.relative_to(root)}:{block.start_line}: {exc}"
                )
                continue
            examples.append(
                {
                    "path": path,
                    "line": block.start_line,
                    "value": value,
                    "text": block.text,
                }
            )
    return examples, errors


def walk_values(value: Any, path: tuple[str, ...] = ()) -> Iterable[tuple[tuple[str, ...], Any]]:
    yield path, value
    if isinstance(value, dict):
        for key, child in value.items():
            yield from walk_values(child, path + (str(key),))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk_values(child, path + (str(index),))


def validate(root: Path, zip_path: Path | None = None) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    metrics: dict[str, Any] = {}
    checks: list[dict[str, str]] = []

    def add_check(name: str, ok: bool, details: str, *, warning: bool = False) -> None:
        status = "PASS" if ok else ("WARN" if warning else "FAIL")
        checks.append({"name": name, "status": status, "details": details})
        if not ok:
            (warnings if warning else errors).append(f"{name}: {details}")

    required = [
        "README.md",
        "VERSION.md",
        "CHANGELOG.md",
        "REQUIREMENTS_COVERAGE.md",
        "MIGRATION_FROM_v0.2.0.md",
        "MIGRATION_FROM_v0.3.0.md",
        "MIGRATION_FROM_v0.3.1.md",
        "MIGRATION_FROM_v0.4.0.md",
        "MIGRATION_FROM_v0.4.1.md",
        GUIDE_NAME,
        FULL_NAME,
        "FILE_INDEX.md",
        "VALIDATION_REPORT.md",
        "MANIFEST.sha256",
        "registries/id_prefixes.yaml",
        "registries/project_profiles.yaml",
        "registries/statuses.yaml",
        "registries/request_routing.yaml",
        "registries/capabilities.yaml",
        "registries/contracts.yaml",
        "registries/implementation_levels.yaml",
        "tools/validate_documentation.py",
    ]
    missing = [rel for rel in required if not (root / rel).exists()]
    add_check(
        "Required artifacts",
        not missing,
        "all present" if not missing else f"missing={missing}",
    )

    all_files = sorted(path for path in root.rglob("*") if path.is_file())
    md_files = [path for path in all_files if path.suffix.lower() == ".md"]
    yaml_files = [
        path for path in all_files if path.suffix.lower() in {".yaml", ".yml"}
    ]
    metrics.update(files=len(all_files), markdown=len(md_files), yaml=len(yaml_files))
    symlinks = [str(path.relative_to(root)) for path in root.rglob("*") if path.is_symlink()]
    add_check(
        "Archive hygiene",
        not symlinks,
        f"files={len(all_files)}, symlinks=0" if not symlinks else f"symlinks={symlinks}",
    )

    unexpected = [
        str(path.relative_to(root))
        for path in all_files
        if path.suffix.lower() not in {".md", ".yaml", ".yml", ".py", ".sha256"}
        and path.name != "MANIFEST.sha256"
    ]
    add_check(
        "File types",
        not unexpected,
        "expected types only" if not unexpected else f"unexpected={unexpected}",
    )

    h1_errors: list[str] = []
    fence_errors: list[str] = []
    metadata_errors: list[str] = []
    for path in md_files:
        text = path.read_text(encoding="utf-8")
        h1_count = sum(1 for line in text.splitlines() if re.match(r"^#\s+", line))
        if h1_count != 1:
            h1_errors.append(f"{path.relative_to(root)}={h1_count}")
        fence_count = sum(1 for line in text.splitlines() if FENCE_PATTERN.match(line))
        if fence_count % 2:
            fence_errors.append(str(path.relative_to(root)))
        baseline_metadata = f"**Версия:** {VERSION}" in text and f"**Дата:** {DATE}" in text
        wip_addendum_metadata = (f"**Версия:** 0.5.1-WIP" in text and
                                 f"**Дата:** 2026-10-25" in text)
        if not (baseline_metadata or wip_addendum_metadata):
            metadata_errors.append(str(path.relative_to(root)))
    add_check(
        "Markdown structure",
        not h1_errors and not fence_errors,
        f"one H1 in {len(md_files)} files; balanced fences"
        if not h1_errors and not fence_errors
        else f"H1={h1_errors[:10]}, fences={fence_errors[:10]}",
    )
    add_check(
        "Metadata",
        not metadata_errors,
        f"version/date present in {len(md_files)} Markdown files"
        if not metadata_errors
        else f"invalid={metadata_errors[:20]}",
    )

    broken_links: list[str] = []
    escaping_links: list[str] = []
    link_count = 0
    for path in md_files:
        text = path.read_text(encoding="utf-8")
        for match in MD_LINK_PATTERN.finditer(text):
            raw = match.group(1).strip().strip("<>")
            if not raw or raw.startswith(("http://", "https://", "mailto:", "#", "data:")):
                continue
            raw = raw.split()[0].strip("\"'")
            target_raw = unquote(raw.split("#", 1)[0].split("?", 1)[0])
            if not target_raw:
                continue
            link_count += 1
            target = (path.parent / target_raw).resolve()
            try:
                target.relative_to(root.resolve())
            except ValueError:
                escaping_links.append(f"{path.relative_to(root)} -> {raw}")
                continue
            if not target.exists():
                broken_links.append(f"{path.relative_to(root)} -> {raw}")
    metrics["local_links"] = link_count
    add_check(
        "Relative links",
        not broken_links and not escaping_links,
        f"checked={link_count}, broken=0, escaping=0"
        if not broken_links and not escaping_links
        else f"broken={broken_links[:20]}, escaping={escaping_links[:20]}",
    )

    loaded: dict[str, Any] = {}
    registry_errors: list[str] = []
    for path in yaml_files:
        try:
            loaded[path.relative_to(root).as_posix()] = yaml.safe_load(
                path.read_text(encoding="utf-8")
            )
        except Exception as exc:
            registry_errors.append(f"{path.relative_to(root)}: {exc}")
    add_check(
        "YAML registries",
        not registry_errors,
        f"parsed={len(yaml_files)}" if not registry_errors else str(registry_errors),
    )

    semantic_files = semantic_markdown_files(root)
    yaml_examples, yaml_example_errors = iter_yaml_examples(semantic_files, root)
    metrics["yaml_examples"] = len(yaml_examples)
    add_check(
        "YAML contract syntax",
        not yaml_example_errors,
        f"parsed={len(yaml_examples)} fenced examples"
        if not yaml_example_errors
        else f"errors={yaml_example_errors[:20]}",
    )

    id_data = loaded.get("registries/id_prefixes.yaml", {}) or {}
    id_entries = (((id_data.get("registry") or {}).get("entries")) or [])
    prefixes = [str(entry.get("prefix")) for entry in id_entries]
    duplicate_prefixes = sorted(
        {prefix for prefix in prefixes if prefixes.count(prefix) > 1}
    )
    add_check(
        "ID Registry uniqueness",
        not duplicate_prefixes,
        f"prefixes={len(prefixes)}, duplicates=0"
        if not duplicate_prefixes
        else f"duplicates={duplicate_prefixes}",
    )
    prefix_set = set(prefixes)

    used_prefixes: dict[str, list[str]] = {}
    for path in semantic_files:
        text = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), 1):
            for match in ID_PATTERN.finditer(line):
                prefix = match.group(1)
                if prefix in FALSE_ID_PREFIXES:
                    continue
                used_prefixes.setdefault(prefix, []).append(
                    f"{path.relative_to(root)}:{line_no}"
                )
    unknown_prefixes = sorted(set(used_prefixes) - prefix_set)
    add_check(
        "ID Registry coverage",
        not unknown_prefixes,
        f"used={len(used_prefixes)}, unknown=0"
        if not unknown_prefixes
        else "; ".join(
            f"{prefix}: {used_prefixes[prefix][:3]}" for prefix in unknown_prefixes
        ),
    )

    legacy_hits: list[str] = []
    for path in semantic_files:
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if LEGACY_ID_PATTERN.search(line):
                legacy_hits.append(f"{path.relative_to(root)}:{line_no}: {line.strip()}")
    add_check(
        "Legacy aliases",
        not legacy_hits,
        "none in current normative source documents"
        if not legacy_hits
        else f"hits={legacy_hits[:20]}",
    )

    profile_data = loaded.get("registries/project_profiles.yaml", {}) or {}
    profile_entries = (((profile_data.get("registry") or {}).get("entries")) or [])
    profiles = [str(entry.get("key")) for entry in profile_entries]
    profile_docs = [
        root / "00_Overview/05_Project_Lifecycle_and_Profiles.md",
        root / "11_Appendices/02_Project_Profile_Matrix.md",
        root / "12_Implementation_Specifications/18_Registries_Lifecycles_and_Contract_Normalization.md",
    ]
    missing_profile_mentions: list[str] = []
    for path in profile_docs:
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        for profile in profiles:
            if profile not in text:
                missing_profile_mentions.append(f"{path.relative_to(root)}:{profile}")
    add_check(
        "Profile Registry consistency",
        not missing_profile_mentions,
        f"profiles={len(profiles)} represented in canonical views"
        if not missing_profile_mentions
        else f"missing={missing_profile_mentions[:30]}",
    )

    routing_data = loaded.get("registries/request_routing.yaml", {}) or {}
    routing_registry = routing_data.get("registry") or {}
    single_entry_path = root / "12_Implementation_Specifications/01_Single_Entry_Request_Contract.md"
    single_entry = single_entry_path.read_text(encoding="utf-8")
    enum_errors: list[str] = []
    for group in ("request_classes", "request_modes", "internal_operations"):
        actual = marked_enum_values(single_entry, group)
        expected = [str(value) for value in routing_registry.get(group, [])]
        if actual != expected:
            enum_errors.append(f"{group}: expected={expected}, actual={actual}")
    add_check(
        "Request routing enum equality",
        not enum_errors,
        "classes, modes and internal operations exactly match registry"
        if not enum_errors
        else "; ".join(enum_errors),
    )

    routing_value_errors: list[str] = []
    routing_value_count = 0
    routing_sets = {
        "request_class": set(routing_registry.get("request_classes") or []),
        "mode": set(routing_registry.get("request_modes") or []),
        "operation": set(routing_registry.get("internal_operations") or []),
    }
    for example in yaml_examples:
        value = example["value"]
        if not isinstance(value, dict):
            continue
        for root_key, payload in value.items():
            if not isinstance(payload, dict):
                continue
            candidates: list[tuple[str, Any]] = []
            if root_key == "request":
                classification = payload.get("classification") or {}
                if isinstance(classification, dict):
                    candidates.extend(
                        [
                            ("request_class", classification.get("request_class")),
                            ("mode", classification.get("mode")),
                        ]
                    )
            elif root_key == "request_plan":
                candidates.extend(
                    [
                        ("request_class", payload.get("request_class")),
                        ("mode", payload.get("mode")),
                    ]
                )
                routes = payload.get("routes") or []
                if isinstance(routes, list):
                    candidates.extend(
                        ("operation", route.get("operation"))
                        for route in routes
                        if isinstance(route, dict)
                    )
            elif root_key == "request_trace":
                spans = payload.get("spans") or []
                if isinstance(spans, list):
                    for span in spans:
                        attributes = span.get("attributes") if isinstance(span, dict) else None
                        if isinstance(attributes, dict):
                            candidates.extend(
                                [
                                    ("request_class", attributes.get("request_class")),
                                    ("mode", attributes.get("mode")),
                                ]
                            )
            for field, candidate in candidates:
                if candidate is None:
                    continue
                routing_value_count += 1
                if candidate not in routing_sets[field]:
                    routing_value_errors.append(
                        f"{example['path'].relative_to(root)}:{example['line']}:"
                        f"{root_key}.{field}={candidate}"
                    )
    add_check(
        "Request routing value applicability",
        not routing_value_errors,
        f"uses={routing_value_count}, unknown=0"
        if not routing_value_errors
        else f"errors={routing_value_errors[:30]}",
    )

    statuses_data = loaded.get("registries/statuses.yaml", {}) or {}
    status_groups = ((statuses_data.get("registry") or {}).get("groups")) or {}
    capabilities_data = loaded.get("registries/capabilities.yaml", {}) or {}
    capability_entries = (((capabilities_data.get("registry") or {}).get("entries")) or [])
    capabilities = [str(entry.get("key")) for entry in capability_entries]
    capability_set = set(capabilities)
    spec18_path = root / "12_Implementation_Specifications/18_Registries_Lifecycles_and_Contract_Normalization.md"
    spec18 = spec18_path.read_text(encoding="utf-8")
    matrix_errors: list[str] = []
    expected_matrices = {
        "statuses": generated_status_matrix(status_groups),
        "request_routing": generated_request_routing_matrix(routing_registry),
        "capabilities": generated_capabilities_matrix(capability_entries),
    }
    for name, expected in expected_matrices.items():
        actual = extract_marked_body(spec18, "REGISTRY-MATRIX", name)
        if actual != expected:
            matrix_errors.append(name)
    add_check(
        "Registry-generated matrices",
        not matrix_errors,
        "status, routing and capability views exactly match YAML registries"
        if not matrix_errors
        else f"stale={matrix_errors}",
    )

    contracts_data = loaded.get("registries/contracts.yaml", {}) or {}
    contracts_registry = contracts_data.get("registry") or {}
    contract_entities: dict[str, dict[str, Any]] = contracts_registry.get("entities") or {}
    field_contracts: dict[str, dict[str, Any]] = contracts_registry.get("field_contracts") or {}
    catalog_errors: list[str] = []
    allowed_non_lifecycle = {"IMMUTABLE_RECORD", "IMMUTABLE_CONFIG", "VERSIONED_CONFIG", "GENERATED_INDEX"}
    for entity, metadata in contract_entities.items():
        prefix = metadata.get("id_prefix")
        lifecycle = metadata.get("lifecycle")
        persistence = metadata.get("persistence")
        if prefix is not None and prefix not in prefix_set:
            catalog_errors.append(f"{entity}: unknown prefix {prefix}")
        if lifecycle not in status_groups and lifecycle not in allowed_non_lifecycle:
            catalog_errors.append(f"{entity}: unknown lifecycle {lifecycle}")
        if persistence == "PERSISTENT":
            if not metadata.get("storage_path"):
                catalog_errors.append(f"{entity}: missing storage_path")
            if not metadata.get("revision_policy"):
                catalog_errors.append(f"{entity}: missing revision_policy")
    for entity, rules in field_contracts.items():
        if entity not in contract_entities:
            catalog_errors.append(f"{entity}: field contract without entity")
        overlap = set(rules.get("required_fields") or []) & set(
            rules.get("forbidden_fields") or []
        )
        if overlap:
            catalog_errors.append(f"{entity}: required/forbidden overlap {sorted(overlap)}")
    add_check(
        "Contract Catalog integrity",
        not catalog_errors,
        f"entities={len(contract_entities)}, field contracts={len(field_contracts)}"
        if not catalog_errors
        else f"errors={catalog_errors[:30]}",
    )

    entity_examples: list[dict[str, Any]] = []
    unknown_entity_examples: list[str] = []
    for example in yaml_examples:
        value = example["value"]
        if not isinstance(value, dict):
            continue
        for entity, payload in value.items():
            if not isinstance(payload, dict) or "id" not in payload:
                continue
            record = {
                "path": example["path"],
                "line": example["line"],
                "entity": str(entity),
                "payload": payload,
            }
            entity_examples.append(record)
            if entity not in contract_entities:
                unknown_entity_examples.append(
                    f"{example['path'].relative_to(root)}:{example['line']}:{entity}"
                )
    add_check(
        "Contract Catalog example coverage",
        not unknown_entity_examples,
        f"standalone examples={len(entity_examples)}, uncatalogued=0"
        if not unknown_entity_examples
        else f"uncatalogued={unknown_entity_examples[:30]}",
    )

    prefix_errors: list[str] = []
    status_errors: list[str] = []
    field_errors: list[str] = []
    for example in entity_examples:
        entity = example["entity"]
        if entity not in contract_entities:
            continue
        payload = example["payload"]
        metadata = contract_entities[entity]
        expected_prefix = metadata.get("id_prefix")
        actual_prefix = id_prefix(payload.get("id"))
        if expected_prefix and actual_prefix != expected_prefix:
            prefix_errors.append(
                f"{example['path'].relative_to(root)}:{example['line']}:{entity} "
                f"id={payload.get('id')} expected={expected_prefix}"
            )
        lifecycle = metadata.get("lifecycle")
        if lifecycle in status_groups:
            status = payload.get("status")
            if status is None:
                status_errors.append(
                    f"{example['path'].relative_to(root)}:{example['line']}:{entity} missing status"
                )
            elif status not in status_groups[lifecycle]:
                status_errors.append(
                    f"{example['path'].relative_to(root)}:{example['line']}:{entity} "
                    f"status={status} group={lifecycle}"
                )
        rules = field_contracts.get(entity)
        if rules:
            missing_fields = [
                field for field in rules.get("required_fields") or [] if field not in payload
            ]
            forbidden_fields = [
                field for field in rules.get("forbidden_fields") or [] if field in payload
            ]
            variant = ((rules.get("variants") or {}).get(payload.get("status"))) or {}
            missing_fields.extend(
                field for field in variant.get("required_fields") or [] if field not in payload
            )
            forbidden_fields.extend(
                field for field in variant.get("forbidden_fields") or [] if field in payload
            )
            if missing_fields or forbidden_fields:
                field_errors.append(
                    f"{example['path'].relative_to(root)}:{example['line']}:{entity} "
                    f"missing={sorted(set(missing_fields))}, "
                    f"forbidden={sorted(set(forbidden_fields))}"
                )
    add_check(
        "Entity ID prefix semantics",
        not prefix_errors,
        f"validated={len(entity_examples)} examples"
        if not prefix_errors
        else f"errors={prefix_errors[:30]}",
    )
    add_check(
        "Lifecycle status applicability",
        not status_errors,
        f"validated={len(entity_examples)} examples against entity status groups"
        if not status_errors
        else f"errors={status_errors[:30]}",
    )
    add_check(
        "Canonical contract fields",
        not field_errors,
        f"validated={sum(1 for example in entity_examples if example['entity'] in field_contracts)} focused examples"
        if not field_errors
        else f"errors={field_errors[:30]}",
    )

    capability_errors: list[str] = []
    accounting_errors: list[str] = []
    capability_uses = 0
    for example in yaml_examples:
        value = example["value"]
        for path_tuple, child in walk_values(value):
            if not path_tuple:
                continue
            key = path_tuple[-1]
            if key in FORBIDDEN_ACCOUNTING_KEYS:
                accounting_errors.append(
                    f"{example['path'].relative_to(root)}:{example['line']}:{'.'.join(path_tuple)}"
                )
            is_capability_field = key in CAPABILITY_FIELDS
            if (
                key == "prohibited_operations"
                and len(path_tuple) >= 2
                and path_tuple[-2] == "skill"
            ):
                is_capability_field = True
            if not is_capability_field:
                continue
            values = child if isinstance(child, list) else [child]
            for item in values:
                if not isinstance(item, str):
                    continue
                capability_uses += 1
                if item not in capability_set:
                    capability_errors.append(
                        f"{example['path'].relative_to(root)}:{example['line']}:"
                        f"{'.'.join(path_tuple)}={item}"
                    )
    add_check(
        "Capability Registry applicability",
        not capability_errors,
        f"uses={capability_uses}, unknown=0"
        if not capability_errors
        else f"errors={capability_errors[:30]}",
    )
    add_check(
        "Billing/token accounting exclusion",
        not accounting_errors,
        "no provider billing, cost or token-ledger fields in YAML contracts"
        if not accounting_errors
        else f"forbidden={accounting_errors[:30]}",
    )

    roadmap_path = root / "09_Delivery/02_Implementation_Roadmap.md"
    roadmap_text = roadmap_path.read_text(encoding="utf-8")
    roadmap_lines = roadmap_text.splitlines()
    roadmap_entries: list[tuple[str, str, list[str]]] = []
    for index, line in enumerate(roadmap_lines):
        heading = ROADMAP_HEADING_PATTERN.match(line)
        if not heading:
            continue
        package_id, title = heading.groups()
        dependencies: list[str] = []
        for following in roadmap_lines[index + 1 : index + 7]:
            if following.startswith("### "):
                break
            if following.startswith("**Dependencies:**"):
                dependencies = re.findall(r"\bWP-HARNESS-\d{3}\b", following)
                break
        roadmap_entries.append((package_id, title, dependencies))
    roadmap_errors: list[str] = []
    roadmap_ids = [entry[0] for entry in roadmap_entries]
    duplicate_roadmap_ids = sorted(
        {package_id for package_id in roadmap_ids if roadmap_ids.count(package_id) > 1}
    )
    if duplicate_roadmap_ids:
        roadmap_errors.append(f"duplicate IDs={duplicate_roadmap_ids}")
    roadmap_id_set = set(roadmap_ids)
    for package_id, _title, dependencies in roadmap_entries:
        missing_dependencies = sorted(set(dependencies) - roadmap_id_set)
        if missing_dependencies:
            roadmap_errors.append(
                f"{package_id}: unknown dependencies={missing_dependencies}"
            )
    graph = {package_id: list(dependencies) for package_id, _title, dependencies in roadmap_entries}
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return False
        if node in visited:
            return True
        visiting.add(node)
        for dependency in graph.get(node, []):
            if dependency in graph and not visit(dependency):
                return False
        visiting.remove(node)
        visited.add(node)
        return True

    for package_id in graph:
        if not visit(package_id):
            roadmap_errors.append(f"dependency cycle involving {package_id}")
            break

    spec07 = (
        root / "12_Implementation_Specifications/07_Causal_Development_Sequence.md"
    ).read_text(encoding="utf-8")
    spec07_entries = [
        match.groups()
        for line in spec07.splitlines()
        if (match := ROADMAP_TABLE_PATTERN.match(line))
    ]
    expected_pairs = [(package_id, title) for package_id, title, _deps in roadmap_entries]
    if spec07_entries != expected_pairs:
        roadmap_errors.append(
            f"causal sequence table differs: roadmap={expected_pairs}, sequence={spec07_entries}"
        )
    legacy_implementation_ids: list[str] = []
    for path in semantic_files:
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"\bHNS-(?!REQ-)\d{3}\b", line):
                legacy_implementation_ids.append(
                    f"{path.relative_to(root)}:{line_no}:{line.strip()}"
                )
    if legacy_implementation_ids:
        roadmap_errors.append(
            f"legacy implementation IDs={legacy_implementation_ids[:20]}"
        )
    add_check(
        "Roadmap identity and dependencies",
        not roadmap_errors and len(roadmap_entries) == 14,
        f"packages={len(roadmap_entries)}, unique IDs, exact causal table, acyclic dependencies"
        if not roadmap_errors and len(roadmap_entries) == 14
        else f"errors={roadmap_errors}, packages={len(roadmap_entries)}",
    )

    semantic_text = "\n".join(
        path.read_text(encoding="utf-8") for path in semantic_files
    )
    forbidden_patterns = {
        "separate Attempt edge": r"→\s*Attempt\b",
        "Run / Attempt entity": r"Run\s*/\s*Attempt",
        "old contract_set formula": r"contract_set\(",
        "compensation as Change Pack lifecycle": r"(?m)^\s*status:\s*PARTIALLY_COMPENSATED\s*$",
    }
    semantic_hits = [
        name for name, pattern in forbidden_patterns.items()
        if re.search(pattern, semantic_text)
    ]
    add_check(
        "Lifecycle normalization",
        not semantic_hits,
        "Run-as-attempt, compensation and parallelism rules normalized"
        if not semantic_hits
        else f"violations={semantic_hits}",
    )

    prompt_status_errors: list[str] = []
    for path in semantic_files:
        for block in fenced_blocks(path.read_text(encoding="utf-8")):
            if (
                "prompt_plan:" in block.text
                and re.search(r"(?m)^\s*status:\s*COMPILED\s*$", block.text)
            ):
                prompt_status_errors.append(str(path.relative_to(root)))
    add_check(
        "Prompt lifecycle",
        not prompt_status_errors,
        "COMPILED appears only on Compiled Prompt Bundle"
        if not prompt_status_errors
        else f"violations={prompt_status_errors}",
    )

    spec_files = implementation_spec_files(root)
    missing_specs = [
        prefix
        for prefix in EXPECTED_SPECS
        if not any(path.name.startswith(prefix) for path in spec_files)
    ]
    thin_specs: list[str] = []
    for path in spec_files:
        text = path.read_text(encoding="utf-8")
        if len(text.splitlines()) < 150 or "Критерии приёмки" not in text:
            thin_specs.append(str(path.relative_to(root)))
    add_check(
        "Implementation specifications",
        not missing_specs and not thin_specs,
        "24 files; each >=150 lines and has acceptance criteria"
        if not missing_specs and not thin_specs
        else f"missing={missing_specs}, incomplete={thin_specs}",
    )

    guide_path = root / GUIDE_NAME
    expected_guide = guide_aggregate_text(root)
    actual_guide = guide_path.read_text(encoding="utf-8") if guide_path.exists() else ""
    guide_markers = actual_guide.count("<!-- SOURCE:")
    add_check(
        "Consolidated guide freshness",
        actual_guide == expected_guide and guide_markers == 24,
        f"source markers={guide_markers}/24; content reproducible"
        if actual_guide == expected_guide and guide_markers == 24
        else f"source markers={guide_markers}/24; stale={actual_guide != expected_guide}",
    )

    full_path = root / FULL_NAME
    expected_full = full_aggregate_text(root)
    actual_full = full_path.read_text(encoding="utf-8") if full_path.exists() else ""
    expected_sources = source_markdown_files(root)
    missing_full_markers = [
        path.relative_to(root).as_posix()
        for path in expected_sources
        if f"<!-- SOURCE: {path.relative_to(root).as_posix()} -->" not in actual_full
    ]
    add_check(
        "Full aggregate freshness",
        actual_full == expected_full and not missing_full_markers,
        f"sources={len(expected_sources)}, content reproducible"
        if actual_full == expected_full and not missing_full_markers
        else f"missing markers={missing_full_markers[:20]}, stale={actual_full != expected_full}",
    )

    index_path = root / "FILE_INDEX.md"
    expected_index = file_index_text(root)
    actual_index = index_path.read_text(encoding="utf-8") if index_path.exists() else ""
    add_check(
        "File index freshness",
        actual_index == expected_index,
        "file inventory, line and byte counts are current"
        if actual_index == expected_index
        else "FILE_INDEX.md is stale",
    )

    req_path = root / "REQUIREMENTS_COVERAGE.md"
    req_text = req_path.read_text(encoding="utf-8") if req_path.exists() else ""
    req_ids = re.findall(r"\bHNS-REQ-(\d{3})\b", req_text)
    duplicate_req = sorted({item for item in req_ids if req_ids.count(item) > 1})
    declared_match = re.search(r"\*\*Активных требований:\*\*\s*(\d+)", req_text)
    declared = int(declared_match.group(1)) if declared_match else -1
    add_check(
        "Requirements coverage",
        not duplicate_req and declared == len(set(req_ids)),
        f"unique={len(set(req_ids))}, declared={declared}"
        if not duplicate_req
        else f"duplicates={duplicate_req}, declared={declared}",
    )

    questionnaire = (
        root / "12_Implementation_Specifications/21_Project_Start_Questionnaire.md"
    ).read_text(encoding="utf-8")
    questionnaire_terms = ["документац", "7–12", "15", "не знаю", "3–5"]
    missing_questionnaire = [
        term for term in questionnaire_terms if term.lower() not in questionnaire.lower()
    ]
    add_check(
        "Questionnaire contract",
        not missing_questionnaire,
        "documentation-first, bounded batches, unknown path and limits present"
        if not missing_questionnaire
        else f"missing={missing_questionnaire}",
    )

    brownfield = (
        root / "12_Implementation_Specifications/20_Brownfield_Project_Onboarding.md"
    ).read_text(encoding="utf-8")
    brownfield_terms = [
        "read-only",
        "CONTINUE_DEVELOPMENT",
        "IMPROVE_PROJECT",
        "FIX_KNOWN_BUGS",
        "STABILIZE_BASELINE",
    ]
    missing_brownfield = [term for term in brownfield_terms if term not in brownfield]
    add_check(
        "Brownfield contract",
        not missing_brownfield,
        "read-only inventory and four route families present"
        if not missing_brownfield
        else f"missing={missing_brownfield}",
    )

    mvp = (root / "09_Delivery/01_MVP_Scope.md").read_text(encoding="utf-8")
    mvp_terms = [
        "## 2. Реализованный Core scope",
        "## 4. Hardening после Core",
        "atomic Task",
        "parallel batches",
        "permanent non-goal",
        "READY_FOR_CODEX",
    ]
    missing_mvp = [term for term in mvp_terms if term not in mvp]
    add_check(
        "Core MVP and Hardening boundary",
        not missing_mvp,
        "first vertical loop is separated from concurrency and maintenance hardening"
        if not missing_mvp
        else f"missing={missing_mvp}",
    )

    decisions = (
        root / "11_Appendices/04_Risks_Decisions_and_Open_Questions.md"
    ).read_text(encoding="utf-8")
    decision_rows = [
        line for line in decisions.splitlines()
        if line.startswith("| ") and "WP-HARNESS-" in line and "ADR-" in line
    ]
    add_check(
        "Implementation decision gates",
        len(decision_rows) >= 10
        and "Default owner role" in decisions
        and "Resolve before" in decisions,
        f"gated decisions={len(decision_rows)}, each with owner and ADR output"
        if len(decision_rows) >= 10
        else f"gated decisions={len(decision_rows)}",
    )

    manifest_path = root / "MANIFEST.sha256"
    manifest = parse_manifest(manifest_path)
    actual_rel = sorted(
        path.relative_to(root).as_posix()
        for path in all_files
        if path.name != "MANIFEST.sha256"
    )
    missing_manifest = sorted(set(actual_rel) - set(manifest))
    extra_manifest = sorted(set(manifest) - set(actual_rel))
    bad_hash = [
        rel
        for rel, digest in manifest.items()
        if (root / rel).exists() and sha256(root / rel) != digest
    ]
    add_check(
        "Manifest",
        bool(manifest) and not missing_manifest and not extra_manifest and not bad_hash,
        f"entries={len(manifest)}, hashes verified"
        if manifest and not missing_manifest and not extra_manifest and not bad_hash
        else f"missing={missing_manifest[:10]}, extra={extra_manifest[:10]}, bad={bad_hash[:10]}",
    )

    if zip_path:
        if zip_path.exists():
            try:
                with zipfile.ZipFile(zip_path) as archive:
                    bad_entry = archive.testzip()
                    archive_names = sorted(
                        info.filename
                        for info in archive.infolist()
                        if not info.is_dir()
                    )
                expected_archive_names = sorted(
                    f"{root.name}/{path.relative_to(root).as_posix()}"
                    for path in all_files
                )
                archive_match = archive_names == expected_archive_names
                add_check(
                    "ZIP archive",
                    bad_entry is None and archive_match,
                    f"entries={len(archive_names)}, CRC PASS, tree exact"
                    if bad_entry is None and archive_match
                    else f"bad entry={bad_entry}, tree_exact={archive_match}",
                )
            except Exception as exc:
                add_check("ZIP archive", False, str(exc))
        else:
            add_check("ZIP archive", False, f"not found: {zip_path}")
    else:
        add_check("ZIP archive", False, "zip path not supplied", warning=True)

    source_paths = semantic_files + yaml_files + [root / "tools/validate_documentation.py"]
    metrics["source_tree_hash"] = tree_hash(source_paths, root)
    metrics.update(errors=len(errors), warnings=len(warnings), checks=len(checks))
    return {
        "version": VERSION,
        "date": DATE,
        "validator_version": VALIDATOR_VERSION,
        "status": "PASS" if not errors else "FAIL",
        "root": str(root),
        "zip": str(zip_path) if zip_path else None,
        "metrics": metrics,
        "checks": checks,
        "errors": errors,
        "warnings": warnings,
    }


def write_report(result: dict[str, Any], path: Path) -> None:
    rows = "\n".join(
        f"| {check['name']} | {check['status']} | {check['details'].replace('|', '/')} |"
        for check in result["checks"]
    )
    metrics = result["metrics"]
    report = f"""# Отчёт автоматической и семантической проверки комплекта

**Документ:** Project Harness  
**Версия:** {VERSION}  
**Дата:** {DATE}  
**Статус:** GENERATED VALIDATION REPORT

## Итог

**{result['status']}** — structural and registry/contract semantic documentation validation.

## Область подтверждения

PASS означает, что текущий комплект прошёл перечисленные ниже автоматические проверки: Markdown/package structure, ссылки, YAML syntax, exact registry views, contract catalog coverage, entity-specific ID/status rules, canonical fields, capability values, roadmap identity/dependencies, generated aggregates, manifest and ZIP integrity.

PASS подтверждает только documentation/package artifacts и не заменяет отдельный executable conformance suite движка, security review или provider-adapter tests.

## Сводка

- validator: {VALIDATOR_VERSION};
- файлов: {metrics.get('files', 0)};
- Markdown: {metrics.get('markdown', 0)};
- YAML registries: {metrics.get('yaml', 0)};
- YAML examples: {metrics.get('yaml_examples', 0)};
- локальных ссылок: {metrics.get('local_links', 0)};
- проверок: {metrics.get('checks', 0)};
- ошибок: {metrics.get('errors', 0)};
- предупреждений: {metrics.get('warnings', 0)};
- source tree hash: `sha256:{metrics.get('source_tree_hash', '')}`.

## Результаты

| Проверка | Результат | Детали |
|---|---|---|
{rows}

## Исправленные audit invariants

- implementation packages use `WP-HARNESS-*`; `HNS-REQ-*` remains requirement-only;
- Request Class, Mode and Internal Operation views exactly equal `request_routing.yaml`;
- persistent examples are bound to Contract Catalog, entity ID prefix and lifecycle group;
- canonical field variants and forbidden aliases are validated from `contracts.yaml`;
- capability fields reject values absent from `capabilities.yaml`;
- roadmap IDs, names and dependency graph are checked against the causal sequence;
- generated guide/full document/file index are compared byte-for-byte with reproducible output.

## Ограничение

Этот отчёт подтверждает согласованность documentation/package artifacts версии {VERSION}. Runtime guarantees подтверждаются отдельным `TEST_REPORT_v0.5.0.md` в поставке движка и не выводятся только из этого документационного отчёта.
"""
    path.write_text(report, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--zip", dest="zip_path", type=Path)
    parser.add_argument("--json", dest="json_path", type=Path)
    parser.add_argument("--write-report", dest="report_path", type=Path)
    parser.add_argument("--build-aggregates", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    if args.build_aggregates:
        build_aggregates(root)
    result = validate(root, args.zip_path.resolve() if args.zip_path else None)
    if args.json_path:
        args.json_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    if args.report_path:
        write_report(result, args.report_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
