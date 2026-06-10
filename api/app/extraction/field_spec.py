"""Turn a Pydantic target model into a compact field spec for prompts/heuristics.

Both the LLM mapper and the offline heuristic matcher consume this, so the
target schema stays the single source of truth for what we're mapping toward.
"""

from __future__ import annotations

import typing
from enum import Enum

from pydantic import BaseModel


class FieldSpec(BaseModel):
    name: str
    type: str
    required: bool
    description: str | None = None
    enum_values: list[str] | None = None


def _type_name(annotation: typing.Any) -> tuple[str, list[str] | None]:
    """Render a readable type name and pull enum members if present."""
    args = typing.get_args(annotation)
    # Unwrap Optional[...] / unions to the first non-None member.
    non_none = [a for a in args if a is not type(None)]
    target = non_none[0] if non_none else annotation

    if isinstance(target, type) and issubclass(target, Enum):
        return target.__name__, [m.value for m in target]
    if isinstance(target, type):
        return target.__name__, None
    return str(target), None


def field_specs(model: type[BaseModel]) -> list[FieldSpec]:
    specs: list[FieldSpec] = []
    for name, field in model.model_fields.items():
        type_name, enum_values = _type_name(field.annotation)
        specs.append(
            FieldSpec(
                name=name,
                type=type_name,
                required=field.is_required(),
                description=field.description,
                enum_values=enum_values,
            )
        )
    return specs


def specs_as_text(model: type[BaseModel]) -> str:
    """A human/LLM-readable rendering of the target fields."""
    lines = []
    for s in field_specs(model):
        req = "required" if s.required else "optional"
        enum = f" one of {s.enum_values}" if s.enum_values else ""
        desc = f" — {s.description}" if s.description else ""
        lines.append(f"- {s.name} ({s.type}, {req}{enum}){desc}")
    return "\n".join(lines)
