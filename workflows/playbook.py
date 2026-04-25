from pathlib import Path
from typing import Any

import yaml

from schemas.playbook import Playbook


def load_playbook(path: Path) -> Playbook:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Playbook must be a YAML object: {path}")
    return Playbook.model_validate(raw)


def load_default_playbook() -> Playbook:
    return load_playbook(Path("playbooks/default.yaml"))


def rule_ids_by_route(playbook: Playbook) -> dict[str, list[str]]:
    route_map: dict[str, list[str]] = {}
    for rule in playbook.rules:
        route_map.setdefault(rule.route, []).append(rule.id)
    return route_map


def raw_rule_conditions(playbook: Playbook) -> list[dict[str, Any]]:
    return [rule.when for rule in playbook.rules]
