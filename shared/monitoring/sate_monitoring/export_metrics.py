"""Prometheus-style text exposition for external dashboards."""

from __future__ import annotations

from sate_monitoring.metrics import MetricSample


def render_prometheus(samples: list[MetricSample]) -> str:
    lines: list[str] = []
    for item in samples:
        lines.append(f'# TYPE {item.name} gauge')
        lines.append(f'{item.name}{{group_scope="{item.group_scope}"}} {item.value}')
    return "\n".join(lines) + "\n"
