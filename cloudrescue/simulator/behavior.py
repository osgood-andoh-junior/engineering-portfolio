from backend.topology import Edges, upstream

Faults = dict[str, tuple[str, int]]


def outcome(service: str, edges: Edges, faults: Faults) -> tuple[str, int, str | None]:
    mode, latency = faults[service]
    if mode in {"disconnect", "error"}:
        return mode, latency, None
    ancestors = sorted(upstream(edges, service))
    for parent in ancestors:
        if faults[parent][0] in {"disconnect", "error"}:
            return "dependency", 0, parent
    latency += sum(faults[parent][1] for parent in ancestors if faults[parent][0] == "latency")
    return ("latency" if latency else "healthy"), latency, None
