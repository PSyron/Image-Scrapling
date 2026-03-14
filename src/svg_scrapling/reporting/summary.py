"""Manifest-driven reporting and maintenance utilities."""

from __future__ import annotations

import csv
from collections import Counter
from dataclasses import replace
from pathlib import Path

from svg_scrapling.domain import AssetCandidate, ManifestRecord, PipelineRunSummary
from svg_scrapling.manifests.writer import build_run_summary
from svg_scrapling.storage import RunLayout


def manifest_record_to_candidate(record: ManifestRecord) -> AssetCandidate:
    return AssetCandidate(
        id=record.id,
        query=record.query,
        source_page_url=record.source_page_url,
        asset_url=record.asset_url,
        original_format=record.original_format,
        domain=record.domain,
        title=record.title,
        alt_text=record.alt_text,
        author_or_owner=record.author_or_owner,
        license_hint=record.license_raw,
        style_tags=record.style_tags,
        notes=record.notes,
    )


def build_existing_run_layout(manifest_path: Path) -> RunLayout:
    root = manifest_path.parent.parent
    return RunLayout(
        run_id=root.name,
        root=root,
        originals=root / "originals",
        derived=root / "derived",
        manifests=root / "manifests",
        logs=root / "logs",
        debug=root / "debug",
    )


def build_manifest_summary(
    manifest_path: Path,
    records: tuple[ManifestRecord, ...],
) -> PipelineRunSummary:
    query = records[0].query if records else "unknown"
    run_layout = build_existing_run_layout(manifest_path)
    base_summary = build_run_summary(run_layout.run_id, query, records)

    rejection_counts: Counter[str] = Counter()
    duplicate_counts = Counter(
        record.dedupe_hash for record in records if record.dedupe_hash is not None
    )
    for record in records:
        if record.download_status.value == "failed":
            rejection_counts["download_failed"] += 1
        for note in record.notes:
            if note.startswith("rejection:"):
                rejection_counts[note.removeprefix("rejection:")] += 1

    return replace(
        base_summary,
        rejection_reasons=dict(rejection_counts),
        duplicate_counts={key: count for key, count in duplicate_counts.items() if count > 1},
    )


def render_summary_text(summary: PipelineRunSummary) -> str:
    lines = [
        f"run_id: {summary.run_id}",
        f"query: {summary.query}",
        f"total_discovered: {summary.total_discovered}",
        f"total_downloaded: {summary.total_downloaded}",
        f"total_accepted: {summary.total_accepted}",
        f"total_rejected: {summary.total_rejected}",
        f"total_converted: {summary.total_converted}",
        f"totals_by_format: {summary.totals_by_format}",
        f"totals_by_domain: {summary.totals_by_domain}",
        f"totals_by_reuse_status: {summary.totals_by_reuse_status}",
        f"rejection_reasons: {summary.rejection_reasons}",
        f"conversion_failures: {summary.conversion_failures}",
        f"duplicate_counts: {summary.duplicate_counts}",
    ]
    return "\n".join(lines)


def export_manifest_csv(path: Path, records: tuple[ManifestRecord, ...]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "id",
            "query",
            "asset_url",
            "original_format",
            "domain",
            "license_normalized",
            "reuse_status",
            "download_status",
            "conversion_status",
            "quality_score",
            "stored_original_path",
            "derived_svg_path",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            serialized = record.to_dict()
            writer.writerow({field: serialized[field] for field in fieldnames})
    return path


def export_summary_markdown(path: Path, summary: PipelineRunSummary) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            (
                "# Manifest Summary",
                "",
                f"- Run ID: `{summary.run_id}`",
                f"- Query: `{summary.query}`",
                f"- Total discovered: `{summary.total_discovered}`",
                f"- Total downloaded: `{summary.total_downloaded}`",
                f"- Total accepted: `{summary.total_accepted}`",
                f"- Total rejected: `{summary.total_rejected}`",
                f"- Total converted: `{summary.total_converted}`",
                f"- Totals by format: `{summary.totals_by_format}`",
                f"- Totals by domain: `{summary.totals_by_domain}`",
                f"- Totals by reuse status: `{summary.totals_by_reuse_status}`",
                f"- Rejection reasons: `{summary.rejection_reasons}`",
                f"- Conversion failures: `{summary.conversion_failures}`",
                f"- Duplicates: `{summary.duplicate_counts}`",
            )
        ),
        encoding="utf-8",
    )
    return path
