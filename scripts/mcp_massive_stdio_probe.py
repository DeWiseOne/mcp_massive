#!/usr/bin/env python3
"""
Local smoke test for the Massive MCP server (STDIO transport).

Usage:
  MASSIVE_API_KEY=... python3 scripts/mcp_massive_stdio_probe.py

Notes:
  - This script starts the MCP server as a subprocess and connects via stdio.
  - It lists tools and runs a small smoke test call.
"""

import asyncio
import json
import os
import shutil
import sys


def _require_env(name: str) -> str:
    val = os.getenv(name, "").strip()
    if not val:
        raise SystemExit(f"Missing required env var: {name}")
    return val


async def main() -> None:
    _require_env("MASSIVE_API_KEY")

    # Use the same interpreter that runs this probe so the server sees the same venv/site-packages.
    python = sys.executable
    if not python:
        raise SystemExit("python3 not found in PATH")

    # Import MCP client pieces lazily so errors are clear.
    try:
        from mcp.client.session import ClientSession
        from mcp.client.stdio import StdioServerParameters, stdio_client
    except Exception as exc:
        raise SystemExit(
            "Missing MCP client deps. Install with: pip install 'mcp[cli]'\n"
            f"Import error: {exc}"
        )

    repo_root = __import__("pathlib").Path(__file__).resolve().parents[1]
    src_dir = repo_root / "src"
    # Run via -c with an explicit sys.path insertion so we always use THIS repo's code.
    # This avoids accidental imports from a different environment/site-packages and
    # prevents stdout noise from breaking MCP stdio framing.
    server_entry = (
        "import sys; "
        f"sys.path.insert(0, {str(src_dir)!r}); "
        "from mcp_massive import main; "
        "main()"
    )

    server_params = StdioServerParameters(
        command=python,
        args=["-u", "-c", server_entry],
        env={
            **os.environ,
            "MCP_TRANSPORT": "stdio",
            # Keep PYTHONPATH as-is; we inject src_dir explicitly in server_entry.
        },
    )

    print("STARTING_SERVER stdio ./entrypoint.py", flush=True)
    async with stdio_client(server_params) as (read, write):
        print("CONNECTED stdio streams ready", flush=True)
        # Some MCP servers emit startup logs on stderr (fine). If a server emits
        # anything on stdout it will corrupt the MCP framing; we guard against
        # that by failing fast with a clear message when initialization times out.
        session = ClientSession(read, write)
        print("INITIALIZE ...", flush=True)
        await asyncio.wait_for(session.initialize(), timeout=15)

        print("LIST_TOOLS ...", flush=True)
        tools = await asyncio.wait_for(session.list_tools(), timeout=15)
        print(f"OK: tool_count={len(tools.tools)}")
        print("First tools:", [t.name for t in tools.tools[:10]])

        # Optional smoke call: market status is usually cheap and always available.
        # If this endpoint isn't implemented, you'll still get useful tool listing above.
        tool_name = "get_market_status"
        if any(t.name == tool_name for t in tools.tools):
            res = await session.call_tool(tool_name, {})
            # res.content is a list of content blocks; keep it simple here.
            print("OK: get_market_status returned content blocks:", len(res.content or []))
            if res.content:
                # Print first block compactly
                first = res.content[0]
                try:
                    print("First block:", json.dumps(first.model_dump(), indent=2)[:800])
                except Exception:
                    print("First block:", str(first)[:800])
        else:
            print("NOTE: get_market_status tool not found; skipping smoke call.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
    except asyncio.TimeoutError:
        raise SystemExit(
            "Timed out waiting for MCP handshake. "
            "Try running `MCP_TRANSPORT=stdio python ./entrypoint.py` in one terminal "
            "to confirm the server starts, then re-run this probe."
        )
