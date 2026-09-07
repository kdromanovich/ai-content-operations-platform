#!/usr/bin/env python3
"""Offline structure and configuration checks for the workflows."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = ROOT / "workflows"

EXPECTED = {
    "01-telegram-source-ingestion.json": (14, 14),
    "02-web-source-ingestion.json": (20, 22),
    "03-ai-topic-curation.json": (32, 35),
    "04-telegram-editorial-assistant.json": (37, 37),
    "05-wordpress-publishing-pipeline.json": (30, 29),
    "06-multichannel-text-distribution.json": (43, 45),
    "07-ai-video-production-distribution.json": (139, 154),
}

SECRET_PATTERNS = {
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "Telegram bot token": re.compile(r"(?<![A-Za-z0-9])\d{6,12}:[A-Za-z0-9_-]{20,}(?![A-Za-z0-9])"),
    "JWT": re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"),
    "provider API key": re.compile(r"\b(?:sk|xai|gsk|hf|pat)-[A-Za-z0-9_-]{16,}\b", re.I),
    "literal bearer token": re.compile(r"\bBearer\s+(?!YOUR_)[A-Za-z0-9._~+/-]{16,}={0,2}\b", re.I),
    "literal basic credential": re.compile(r"\bBasic\s+(?!YOUR_)[A-Za-z0-9+/]{16,}={0,2}\b", re.I),
}

ALLOWED_HOSTS = {
    "api.heygen.com",
    "api.openai.com",
    "api.telegram.org",
    "api.vk.com",
    "backend.blotato.com",
    "dzen.ru",
    "example.com",
    "max.ru",
    "n8n.example.com",
    "openrouter.ai",
    "platform-api.max.ru",
    "rssexport.rbc.ru",
    "t.me",
    "vk.com",
    "www.interfax.ru",
    "www.kommersant.ru",
    "www.vedomosti.ru",
}

URL_RE = re.compile(r"https?://[A-Za-z0-9._-]+", re.I)
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@([A-Z0-9.-]+\.[A-Z]{2,})\b", re.I)
CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")
NODE_REFERENCE_PATTERNS = (
    re.compile(r"\$\(\s*(['\"])(.*?)\1\s*\)"),
    re.compile(r"\$node\s*\[\s*(['\"])(.*?)\1\s*\]"),
    re.compile(r"\$items\s*\(\s*(['\"])(.*?)\1"),
)


def walk(value: Any, path: tuple[Any, ...] = ()) -> Iterable[tuple[tuple[Any, ...], Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = path + (key,)
            yield child_path, child
            yield from walk(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_path = path + (index,)
            yield child_path, child
            yield from walk(child, child_path)


def count_edges(connections: dict[str, Any]) -> int:
    total = 0
    for channels in connections.values():
        for output_groups in channels.values():
            for output_group in output_groups:
                total += len(output_group)
    return total


def scalar_text(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(scalar_text(child) for child in value.values())
    if isinstance(value, list):
        return " ".join(scalar_text(child) for child in value)
    return str(value)


def validate_file(path: Path, expected_nodes: int, expected_edges: int) -> list[str]:
    errors: list[str] = []
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - validation should report parser failures
        return [f"{path.name}: invalid JSON: {exc}"]

    nodes = doc.get("nodes")
    connections = doc.get("connections")
    if not isinstance(nodes, list) or not isinstance(connections, dict):
        return [f"{path.name}: missing nodes or connections"]
    if len(nodes) != expected_nodes:
        errors.append(f"{path.name}: expected {expected_nodes} nodes, found {len(nodes)}")
    edges = count_edges(connections)
    if edges != expected_edges:
        errors.append(f"{path.name}: expected {expected_edges} edges, found {edges}")
    if doc.get("active") is not False:
        errors.append(f"{path.name}: workflow must import inactive")
    if doc.get("pinData"):
        errors.append(f"{path.name}: pinData must not be included")

    names = [str(node.get("name", "")) for node in nodes]
    node_ids = [str(node.get("id", "")) for node in nodes]
    name_set = set(names)
    if "" in name_set or len(name_set) != len(names):
        errors.append(f"{path.name}: node names must be present and unique")
    if "" in set(node_ids) or len(set(node_ids)) != len(node_ids):
        errors.append(f"{path.name}: node IDs must be present and unique")
    cyrillic_names = [name for name in names if CYRILLIC_RE.search(name)]
    if cyrillic_names:
        errors.append(f"{path.name}: {len(cyrillic_names)} node names are not English")

    adjacency: dict[str, set[str]] = {name: set() for name in name_set}
    roots = {
        str(node.get("name", ""))
        for node in nodes
        if str(node.get("type", "")).lower().endswith("trigger")
        or node.get("type") == "n8n-nodes-base.webhook"
    }
    for source, channels in connections.items():
        if source not in name_set:
            errors.append(f"{path.name}: unknown connection source {source!r}")
        if any(str(connection_type).startswith("ai_") for connection_type in channels):
            roots.add(source)
        for output_groups in channels.values():
            for output_group in output_groups:
                for target in output_group:
                    target_name = target.get("node")
                    if target_name not in name_set:
                        errors.append(f"{path.name}: unknown connection target {target_name!r}")
                    elif source in adjacency:
                        adjacency[source].add(target_name)

    reachable: set[str] = set()
    pending = list(roots)
    while pending:
        current = pending.pop()
        if current in reachable:
            continue
        reachable.add(current)
        pending.extend(adjacency.get(current, ()))
    unreachable = sorted(name_set - reachable)
    if unreachable:
        errors.append(f"{path.name}: unreachable nodes: {', '.join(unreachable)}")

    for item_path, value in walk(doc):
        key = str(item_path[-1]) if item_path else ""
        location = ".".join(str(part) for part in item_path)
        if key in {"credentials", "webhookId"}:
            errors.append(f"{path.name}: forbidden field {location}")
        if key in {"chatId", "accountId", "workflowId", "folderId", "fileId"} and value not in (None, ""):
            text = scalar_text(value)
            if not any(marker in text for marker in ("YOUR_", "SELECT_", "{{", "$json", "$vars")):
                errors.append(f"{path.name}: non-placeholder identifier at {location}")
        if not isinstance(value, str):
            continue
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(value):
                errors.append(f"{path.name}: possible {label} at {location}")
        for match in EMAIL_RE.finditer(value):
            if match.group(1).lower() != "example.com":
                errors.append(f"{path.name}: non-example email at {location}")
        for match in URL_RE.finditer(value):
            host = (urlsplit(match.group(0)).hostname or "").lower()
            if host and host not in ALLOWED_HOSTS:
                errors.append(f"{path.name}: non-allowlisted URL host at {location}")
        for pattern in NODE_REFERENCE_PATTERNS:
            for match in pattern.finditer(value):
                referenced = match.group(2)
                if referenced not in name_set:
                    errors.append(f"{path.name}: expression references unknown node {referenced!r} at {location}")

    return errors


def validate_repository() -> list[str]:
    errors: list[str] = []
    actual = {path.name for path in WORKFLOW_DIR.glob("*.json")}
    expected = set(EXPECTED)
    for missing in sorted(expected - actual):
        errors.append(f"missing workflow: {missing}")
    for extra in sorted(actual - expected):
        errors.append(f"unexpected workflow: {extra}")
    for name, (node_count, edge_count) in EXPECTED.items():
        path = WORKFLOW_DIR / name
        if path.exists():
            errors.extend(validate_file(path, node_count, edge_count))
    return errors


def main() -> int:
    errors = validate_repository()
    if errors:
        print(f"FAILED: {len(errors)} issue(s)")
        for error in errors:
            print(f"- {error}")
        return 1
    print("PASS: 7 workflows, 315 nodes, 336 edges")
    print("PASS: topology, reachability, node references, inactive state, identifiers, URL hosts, and secret patterns")
    return 0


if __name__ == "__main__":
    sys.exit(main())
