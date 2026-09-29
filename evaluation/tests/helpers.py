"""Shared test helpers."""

from app.schemas import DiagramGraph


def graph(
    nodes: list[tuple], edges: list[tuple] = (), diagram_type: str = "flowchart"
) -> DiagramGraph:
    """nodes: (id, label[, type[, group_id]]); edges: (source, target[, relation[, label]])."""
    return DiagramGraph.model_validate(
        {
            "schema_version": "2.0",
            "diagram_type": diagram_type,
            "nodes": [
                {
                    "id": n[0],
                    "label": n[1],
                    "type": n[2] if len(n) > 2 else "module",
                    "group_id": n[3] if len(n) > 3 else None,
                }
                for n in nodes
            ],
            "edges": [
                {
                    "source": e[0],
                    "target": e[1],
                    "relation": e[2] if len(e) > 2 else "flows_to",
                    "label": e[3] if len(e) > 3 else None,
                }
                for e in edges
            ],
        }
    )
