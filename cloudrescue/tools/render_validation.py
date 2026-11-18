"""Render a compact static chart from the measured experiment JSON."""

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    data = json.loads(args.dataset.read_text(encoding="utf-8"))
    policies = ("baseline", "retry", "breaker", "limit")
    labels = ("Baseline", "Retry", "Breaker", "Rate limiting")
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="450" viewBox="0 0 800 450" role="img">',
        "<title>Modeled and measured mean HTTP request success</title>",
        '<rect width="800" height="450" fill="#101827" rx="14"/>',
        '<g fill="#eef4ff" font-family="system-ui,sans-serif" font-size="15">',
        '<text x="32" y="45" font-size="23" font-weight="700">Request success across three repeats</text>',
        '<text x="32" y="72">CloudRescue loopback simulator · authored fault trace</text>',
    ]
    for index, (policy, label) in enumerate(zip(policies, labels, strict=True)):
        y = 117 + index * 72
        lines.append(f'<text x="32" y="{y + 17}">{label}</text>')
        metric = data["summary"][policy]["request_success"]
        for offset, field, color in (
            (0, "predicted_mean", "#668bfc"),
            (24, "observed_mean", "#52d4b5"),
        ):
            value = metric[field]
            width = max(0, min(1, value)) * 525
            lines.append(
                f'<rect x="155" y="{y + offset}" width="{width:.2f}" height="16" rx="3" fill="{color}"/>'
            )
            lines.append(f'<text x="{165 + width:.2f}" y="{y + offset + 13}">{value:.1%}</text>')
    lines.extend(
        [
            '<text x="32" y="423" fill="#668bfc">■ Modeled</text>',
            '<text x="145" y="423" fill="#52d4b5">■ Measured</text>',
            "</g></svg>",
        ]
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
