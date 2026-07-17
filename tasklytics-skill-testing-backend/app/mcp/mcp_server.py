"""Minimal MCP server exposing get_productivity_stats as an MCP tool.

Standalone from the FastAPI app - MCP tools operate over structured JSON
input, not SQLAlchemy ORM objects, so this takes a plain list-of-dicts task
shape (what a real MCP client can actually send) rather than importing the
ORM-coupled function from app.ai_agents.tools directly.

Run: python app/mcp/mcp_server.py
"""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("tasklytics-productivity")


@mcp.tool()
def get_productivity_stats(tasks: list[dict]) -> dict:
    """Compute productivity statistics from a list of tasks.

    Each task dict must include a boolean "completed" field.
    """
    total = len(tasks)
    completed = len([t for t in tasks if t.get("completed")])

    return {
        "total": total,
        "completed": completed,
        "completion_rate": completed / total if total else 0,
    }


if __name__ == "__main__":
    mcp.run()
