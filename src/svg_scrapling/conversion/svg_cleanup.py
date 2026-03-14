"""Deterministic SVG cleanup, validation, and complexity metrics."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Protocol
from xml.etree import ElementTree as ET


class SvgCleanupError(ValueError):
    """Raised when SVG cleanup or validation cannot complete safely."""


@dataclass(frozen=True)
class SvgCleanupResult:
    cleaned_svg_path: Path
    view_box: str
    width: str
    height: str
    complexity_metrics: dict[str, float]
    notes: tuple[str, ...] = ()


class SvgOptimizer(Protocol):
    def optimize(self, svg_text: str) -> str:
        """Return an optimized SVG string or raise SvgCleanupError."""


@dataclass
class SvgoCommandOptimizer:
    command: tuple[str, ...] = ("svgo",)

    def optimize(self, svg_text: str) -> str:
        with TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "input.svg"
            output_path = Path(tmp_dir) / "output.svg"
            input_path.write_text(svg_text, encoding="utf-8")
            completed = subprocess.run(
                [*self.command, str(input_path), "-o", str(output_path)],
                capture_output=True,
                text=True,
                check=False,
            )
            if completed.returncode != 0:
                error_message = completed.stderr.strip() or completed.stdout.strip()
                raise SvgCleanupError(error_message or "svgo command failed")
            return output_path.read_text(encoding="utf-8")


@dataclass
class SvgPostProcessor:
    optimizer: SvgOptimizer | None = None

    def process(self, input_path: Path, output_path: Path | None = None) -> SvgCleanupResult:
        target_path = output_path or input_path
        raw_svg = input_path.read_text(encoding="utf-8")
        notes: list[str] = []

        if self.optimizer is not None:
            raw_svg = self.optimizer.optimize(raw_svg)
            notes.append("optimized:svgo")

        raw_svg = re.sub(r"<!--.*?-->", "", raw_svg, flags=re.DOTALL)
        try:
            root = ET.fromstring(raw_svg)
        except ET.ParseError as exc:
            raise SvgCleanupError(f"invalid_svg:{exc}") from exc

        if self._local_name(root.tag) != "svg":
            raise SvgCleanupError("root element must be <svg>")

        self._remove_non_structural_elements(root)
        width, height, view_box = self._normalize_dimensions(root)
        metrics = self._complexity_metrics(root)
        cleaned_svg = ET.tostring(root, encoding="unicode")
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(cleaned_svg, encoding="utf-8")

        return SvgCleanupResult(
            cleaned_svg_path=target_path,
            view_box=view_box,
            width=width,
            height=height,
            complexity_metrics=metrics,
            notes=tuple(notes),
        )

    def _remove_non_structural_elements(self, root: ET.Element) -> None:
        removable = {"metadata", "title", "desc", "script"}
        for parent in root.iter():
            children = list(parent)
            for child in children:
                if self._local_name(child.tag) in removable:
                    parent.remove(child)

    def _normalize_dimensions(self, root: ET.Element) -> tuple[str, str, str]:
        width = self._normalize_dimension_value(root.attrib.get("width"))
        height = self._normalize_dimension_value(root.attrib.get("height"))
        view_box = root.attrib.get("viewBox")

        if view_box is None:
            if width is None or height is None:
                raise SvgCleanupError("svg must define width/height or viewBox")
            view_box = f"0 0 {width} {height}"
        else:
            parsed_view_box = self._parse_view_box(view_box)
            if width is None:
                width = parsed_view_box[2]
            if height is None:
                height = parsed_view_box[3]
            view_box = " ".join(parsed_view_box)

        if width is None or height is None:
            raise SvgCleanupError("unable to normalize width and height")

        root.attrib["width"] = width
        root.attrib["height"] = height
        root.attrib["viewBox"] = view_box
        return width, height, view_box

    def _normalize_dimension_value(self, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if normalized.endswith("px"):
            normalized = normalized[:-2]
        try:
            parsed = float(normalized)
        except ValueError:
            raise SvgCleanupError(f"unsupported_dimension:{value}") from None
        if parsed.is_integer():
            return str(int(parsed))
        return f"{parsed:.3f}".rstrip("0").rstrip(".")

    def _parse_view_box(self, value: str) -> tuple[str, str, str, str]:
        parts = value.replace(",", " ").split()
        if len(parts) != 4:
            raise SvgCleanupError("viewBox must contain four numeric values")
        normalized_parts: list[str] = []
        for part in parts:
            try:
                parsed = float(part)
            except ValueError:
                raise SvgCleanupError("viewBox must contain numeric values") from None
            if parsed.is_integer():
                normalized_parts.append(str(int(parsed)))
            else:
                normalized_parts.append(f"{parsed:.3f}".rstrip("0").rstrip("."))
        return tuple(normalized_parts)  # type: ignore[return-value]

    def _complexity_metrics(self, root: ET.Element) -> dict[str, float]:
        max_depth = 0
        element_count = 0
        path_count = 0

        def walk(node: ET.Element, depth: int) -> None:
            nonlocal max_depth, element_count, path_count
            element_count += 1
            max_depth = max(max_depth, depth)
            if self._local_name(node.tag) == "path":
                path_count += 1
            for child in list(node):
                walk(child, depth + 1)

        walk(root, 1)
        return {
            "element_count": float(element_count),
            "path_count": float(path_count),
            "max_depth": float(max_depth),
        }

    def _local_name(self, tag: str) -> str:
        if "}" in tag:
            return tag.split("}", 1)[1]
        return tag
