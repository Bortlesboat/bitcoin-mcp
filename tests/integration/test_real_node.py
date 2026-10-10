"""Exercise MCP tools against a task-owned Core or Knots regtest node.

Set BITCOIN_MCP_TEST_BITCOIND to a verified bitcoind executable to opt in.
The fixture never uses an existing node's configuration, wallet or cookie.
"""

import base64
from collections.abc import Iterator
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from typing import Any
import urllib.request

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import pytest


@pytest.fixture(scope="module")
def real_node(tmp_path_factory: pytest.TempPathFactory) -> Iterator[dict[str, Any]]:
    requested_binary = os.environ.get("BITCOIN_MCP_TEST_BITCOIND")
    if not requested_binary:
        pytest.skip("Set BITCOIN_MCP_TEST_BITCOIND to run real-node integration tests")
    binary = Path(requested_binary).resolve(strict=True)
    datadir = tmp_path_factory.mktemp("bitcoin-mcp-regtest")
    config = datadir / "bitcoin.conf"
    config.write_text("", encoding="utf-8")
    cookie = datadir / "regtest" / ".cookie"
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]

    # Explicit config/data paths keep user settings and wallets out of the run.
    command = [
        str(binary),
        "-regtest",
        f"-datadir={datadir}",
        f"-conf={config}",
        "-server=1",
        f"-rpcport={port}",
        "-rpcbind=127.0.0.1",
        "-rpcallowip=127.0.0.1",
        "-disablewallet",
        "-listen=0",
        "-dnsseed=0",
        "-discover=0",
        "-connect=0",
        "-networkactive=0",
    ]
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def rpc(method: str, *params: Any) -> Any:
        credentials = cookie.read_text(encoding="utf-8").strip()
        authorization = base64.b64encode(credentials.encode()).decode()
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}",
            data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": method,
                             "params": list(params)}).encode(),
            headers={"Content-Type": "application/json",
                     "Authorization": f"Basic {authorization}"},
        )
        with opener.open(request, timeout=2) as response:
            result = json.load(response)
        if result.get("error"):
            raise RuntimeError(result["error"]["message"])
        return result["result"]

    with (datadir / "process.log").open("wb") as log:
        process = subprocess.Popen(
            command,
            stdout=log,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        try:
            deadline = time.monotonic() + 45
            while True:
                if process.poll() is not None:
                    pytest.fail(f"Test node exited with code {process.returncode}; see {datadir}/process.log")
                try:
                    chain = rpc("getblockchaininfo")
                    break
                except (OSError, ValueError, RuntimeError):
                    if time.monotonic() >= deadline:
                        pytest.fail(f"Test node RPC did not become ready; see {datadir}/process.log")
                    time.sleep(0.1)

            assert chain["chain"] == "regtest"
            descriptor = rpc("getdescriptorinfo", "raw(51)")["descriptor"]
            blocks = rpc("generatetodescriptor", 3, descriptor)
            user, password = cookie.read_text(encoding="utf-8").strip().split(":", 1)
            # The SDK adds its minimal platform environment; do not copy secrets.
            environment = {
                "BITCOIN_RPC_HOST": "127.0.0.1",
                "BITCOIN_RPC_PORT": str(port),
                "BITCOIN_RPC_USER": user,
                "BITCOIN_RPC_PASSWORD": password,
                "BITCOIN_DATADIR": str(datadir),
                "BITCOIN_NETWORK": "regtest",
                "SATOSHI_API_URL": "",
                "NO_PROXY": "127.0.0.1,localhost",
            }
            yield {"environment": environment, "blockhash": blocks[-1]}
        finally:
            if process.poll() is None:
                try:
                    rpc("stop")
                except (OSError, ValueError, RuntimeError):
                    process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)


async def _call_tool(environment: dict[str, str], name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "bitcoin_mcp.server"],
        env=environment,
    )
    with anyio.fail_after(30):
        async with stdio_client(parameters) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(name, arguments)
                assert not result.is_error, f"MCP tool failed: {name}"
                text = "".join(item.text for item in result.content if item.type == "text")
                return json.loads(text)


def test_network_info(real_node: dict[str, Any]) -> None:
    result = anyio.run(_call_tool, real_node["environment"], "get_network_info", {})
    assert result["version"] > 0
    assert result["subversion"].startswith(("/Satoshi:", "/Knots:"))
    assert result["connections"] == 0
    assert result["relayfee"] >= 0


def test_blockchain_info(real_node: dict[str, Any]) -> None:
    result = anyio.run(_call_tool, real_node["environment"], "get_blockchain_info", {})
    assert result["chain"] == "regtest"
    assert result["blocks"] == result["headers"] == 3
    assert result["pruned"] is False


def test_block_stats(real_node: dict[str, Any]) -> None:
    result = anyio.run(_call_tool, real_node["environment"], "get_block_stats", {"height": 3})
    assert result["height"] == 3
    assert result["blockhash"] == real_node["blockhash"]
    assert result["txs"] == 1
    assert result["totalfee"] == 0
    assert result["subsidy"] == 5_000_000_000


def test_mempool_info(real_node: dict[str, Any]) -> None:
    result = anyio.run(_call_tool, real_node["environment"], "get_mempool_info", {})
    assert result["size"] == result["bytes"] == 0
    assert result["maxmempool"] > 0
    assert result["mempoolminfee"] >= 0


def test_fee_estimate_without_history(real_node: dict[str, Any]) -> None:
    result = anyio.run(_call_tool, real_node["environment"], "estimate_smart_fee", {"conf_target": 6})
    assert result["conf_target"] == 6
    assert result["fee_rate_btc_kvb"] == result["fee_rate_sat_vb"] == 0
    assert result["errors"], "A fresh regtest chain must report insufficient fee history"
