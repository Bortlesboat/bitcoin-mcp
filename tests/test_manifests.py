import ast
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _is_mcp_tool(decorator: ast.expr) -> bool:
    return (
        isinstance(decorator, ast.Call)
        and isinstance(decorator.func, ast.Attribute)
        and isinstance(decorator.func.value, ast.Name)
        and decorator.func.value.id == "mcp"
        and decorator.func.attr == "tool"
    )


def test_tools_manifest_matches_standard_registered_tools() -> None:
    source = (ROOT / "src" / "bitcoin_mcp" / "server.py").read_text(encoding="utf-8")
    module = ast.parse(source)
    standard_tools = {
        node.name
        for node in module.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and any(_is_mcp_tool(decorator) for decorator in node.decorator_list)
    }

    manifest = json.loads((ROOT / "tools.json").read_text(encoding="utf-8"))
    manifest_tools = {tool["name"] for tool in manifest["tools"]}

    assert manifest["tool_count"] == len(standard_tools) == 50
    assert manifest_tools == standard_tools
    assert {tool["name"] for tool in manifest["conditional_tools"]} == {
        "query_remote_api"
    }

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    llms = (ROOT / "llms.txt").read_text(encoding="utf-8")
    for tool_name in standard_tools:
        assert f"`{tool_name}`" in readme
        assert f"- {tool_name}:" in llms
