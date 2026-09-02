from __future__ import annotations


def _table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _is_example_stub(data: dict) -> bool:
    if data.get("stub") == "example":
        return True
    return any(row.get("status") == "example" for row in (data.get("controls") or []) + (data.get("docs") or []))


def render_inventory_md(data: dict) -> str:
    parts = ["# Product inventory", ""]
    if _is_example_stub(data):
        parts += [
            "> **Example stub — not a live catalog.** Foodora, Foodpanda, and Yemeksepeti here are demo brand codes. Rows below are fixtures, not production.",
            "",
        ]
    parts += ["Generated. Edit `product-inventory.yaml`.", ""]
    parts += ["## Stack", "", _table(["id", "name", "layer", "notes"], [[s["id"], s["name"], s["layer"], s.get("notes") or ""] for s in data["stack"]]), ""]
    parts += ["## Controls", "", _table(
        ["id", "name", "type", "journey", "brands", "status", "owner"],
        [[c["id"], c["name"], c["type"], c["journey"], ",".join(c["brands"]), c["status"], c["owner"]] for c in data["controls"]],
    ), ""]
    parts += ["## Docs", "", _table(
        ["id", "type", "title", "status", "journey", "brands"],
        [[d["id"], d["type"], d["title"], d["status"], d["journey"], ",".join(d["brands"])] for d in data["docs"]],
    ), ""]
    return "\n".join(parts)
