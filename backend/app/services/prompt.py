"""Prompt template helpers shared by REST, WebSocket and agents."""

from __future__ import annotations

import difflib
import re
from typing import Any, Mapping


# Keep the syntax intentionally small and predictable. Dot and dash are useful
# for names such as ``user.name`` and ``output-format`` while still rejecting
# arbitrary expressions.
TEMPLATE_VARIABLE_PATTERN = re.compile(r"{{\s*([A-Za-z_][A-Za-z0-9_.-]*)\s*}}")


def extract_template_variables(content: str) -> list[str]:
    """Return unique placeholders in first-seen order."""

    result: list[str] = []
    for name in TEMPLATE_VARIABLE_PATTERN.findall(content or ""):
        if name not in result:
            result.append(name)
    return result


def normalize_variables(content: str, variables: Any = None) -> list[str]:
    """Normalize explicitly supplied variable names and include placeholders."""

    names: list[str] = []
    if isinstance(variables, Mapping):
        variables = list(variables.keys())
    if isinstance(variables, (list, tuple, set)):
        for value in variables:
            name = str(value).strip()
            if name and name not in names:
                names.append(name)
    for name in extract_template_variables(content):
        if name not in names:
            names.append(name)
    return names


def render_prompt_template(
    content: str,
    values: Mapping[str, Any] | None = None,
    *,
    strict: bool = True,
) -> tuple[str, list[str]]:
    """Render placeholders and return ``(rendered, missing_names)``.

    Values are converted to text without evaluating expressions. In strict
    mode missing values raise ``ValueError``; callers can use non-strict mode
    to preview a template while retaining unresolved placeholders.
    """

    values = values or {}
    missing: list[str] = []

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in values or values[name] is None:
            if name not in missing:
                missing.append(name)
            return match.group(0)
        return str(values[name])

    rendered = TEMPLATE_VARIABLE_PATTERN.sub(replace, content or "")
    if strict and missing:
        raise ValueError(f"缺少模板变量: {', '.join(missing)}")
    return rendered, missing


def unified_prompt_diff(from_content: str, to_content: str) -> str:
    """Create a stable, human-readable unified diff for two versions."""

    return "".join(
        difflib.unified_diff(
            (from_content or "").splitlines(keepends=True),
            (to_content or "").splitlines(keepends=True),
            fromfile="旧版本",
            tofile="新版本",
        )
    )
