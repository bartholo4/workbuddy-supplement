#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Zero-cost dispatcher for WorkBuddy-backed local information-gathering sources.

Read-only toward WorkBuddy installation and user config directories; never prints tokens or keys.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

MCP_REGISTRY: dict[str, dict[str, str]] = {
    "efunds": {
        "dir": "efunds",
        "fallback_url": "https://sc.efunds.com.cn/api/csai-mcp-service/mcp/",
        "desc": "易方达基金画像、指数产业链节点/成分股/估值温度与新闻、公众号文章",
    },
    "orientfutures": {
        "dir": "orientfutures-mobile-knowledge-base",
        "fallback_url": "https://commosmart.orientfutures.com/mcp/knowledge-base",
        "desc": "东证期货审核知识库（交易制度、风险投教、合约资料）",
    },
    "lingyi": {
        "dir": "lingyi-mcp",
        "fallback_url": "",
        "desc": "零一运营（视频号/私域案例与运营知识库）",
    },
    "mindbye": {
        "dir": "mindbye-contract-review",
        "fallback_url": "",
        "desc": "明白律师合同风险审查参考",
    },
    "24haowan": {
        "dir": "24haowan",
        "fallback_url": "https://mcp.24haowan.com/mcp",
        "desc": "24好玩互动营销H5模板与客户案例库",
    },
    "chainlon-geo": {
        "dir": "chainlon-geo-mcp",
        "fallback_url": "",
        "desc": "链龙 GEO AI搜索品牌可见度诊断",
    },
    "hefei-alerts": {
        "dir": "hefei-city-alerts",
        "fallback_url": "",
        "desc": "合肥本地民生通告、停水电、交通管制与天气预警",
    },
}

TRAVEL_KINDS = ("train", "flight", "hotel", "scenery", "bus", "traffic", "travel")
GAOKAO_KINDS = ("scores", "rank")
PREFERRED_LOCAL_MODELS = ("gemini-3.8-flash-high", "gemini-4-carbon-medium", "gemini-4-carbon-high")
LOOPBACK_HOSTS = ("127.0.0.1", "localhost")


def _get_workbuddy_home() -> Path:
    override = os.environ.get("WORKBUDDY_CONFIG_DIR", "").strip()
    return Path(override).expanduser() if override else Path.home() / ".workbuddy"


def _cli_assets_under(app_root: Path) -> tuple[Path, Path] | None:
    for res_name in ("resources", "Resources"):
        cli_dir = app_root / res_name / "app.asar.unpacked" / "cli"
        cli_mjs = cli_dir / "dist" / "codebuddy-lite-wb.mjs"
        product_json = cli_dir / "product.json"
        if cli_mjs.is_file() and product_json.is_file():
            return cli_mjs, product_json
    return None


def _resolve_workbuddy_app() -> tuple[Path, Path, Path, list[str]] | None:
    """Locate WorkBuddy CLI assets and node/Electron launcher cross-platform."""
    candidates: list[Path] = []
    env_app = os.environ.get("WORKBUDDY_APP_DIR", "").strip()
    if env_app:
        candidates.append(Path(env_app).expanduser())

    if sys.platform == "win32" or os.name == "nt":
        local_app = os.environ.get("LOCALAPPDATA", "").strip()
        if local_app:
            candidates.append(Path(local_app) / "Programs" / "WorkBuddy")
        candidates.extend(
            [
                Path(r"C:\Program Files\WorkBuddy"),
                Path(r"C:\Program Files (x86)\WorkBuddy"),
                Path(r"D:\WorkBuddy"),
                Path(r"E:\WorkBuddy"),
            ]
        )
        which_wb = shutil.which("WorkBuddy") or shutil.which("WorkBuddy.exe")
        if which_wb:
            candidates.append(Path(which_wb).resolve().parent)
    elif sys.platform == "darwin":
        candidates.extend(
            [
                Path("/Applications/WorkBuddy.app/Contents"),
                Path.home() / "Applications" / "WorkBuddy.app" / "Contents",
            ]
        )
    else:
        candidates.extend(
            [
                Path("/opt/WorkBuddy"),
                Path("/usr/lib/workbuddy"),
                Path.home() / ".local" / "share" / "WorkBuddy",
            ]
        )

    for root in candidates:
        assets = _cli_assets_under(root)
        if not assets:
            continue
        cli_mjs, product_json = assets
        launcher = _find_cli_launcher(root)
        if launcher:
            return root, cli_mjs, product_json, launcher
    return None


def _find_cli_launcher(app_root: Path) -> list[str] | None:
    if sys.platform == "win32" or os.name == "nt":
        exe = app_root / "WorkBuddy.exe"
        if exe.is_file():
            return [str(exe)]
    elif sys.platform == "darwin":
        exe = app_root / "MacOS" / "WorkBuddy"
        if exe.is_file():
            return [str(exe)]
    else:
        for rel in ("workbuddy", "WorkBuddy"):
            exe = app_root / rel
            if exe.is_file():
                return [str(exe)]
    node_bin = shutil.which("node")
    return [node_bin] if node_bin else None


def _resolve_wechat_script() -> Path | None:
    """Locate sogou_search.py preferring highest cached plugin version."""
    wb_home = _get_workbuddy_home()
    pattern = str(
        wb_home
        / "plugins"
        / "cache"
        / "cb_teams_marketplace"
        / "deep-research"
        / "*"
        / "skills"
        / "wechat-article-search"
        / "scripts"
        / "sogou_search.py"
    )
    matches = sorted(glob.glob(pattern), reverse=True)
    if matches:
        return Path(matches[0])
    fallback = (
        wb_home
        / "plugins"
        / "marketplaces"
        / "cb_teams_marketplace"
        / "plugins"
        / "deep-research"
        / "skills"
        / "wechat-article-search"
        / "scripts"
        / "sogou_search.py"
    )
    return fallback if fallback.is_file() else None


def _resolve_travel_script(kind: str) -> Path | None:
    p = (
        _get_workbuddy_home()
        / "connectors-marketplace"
        / "connectors"
        / "tc-chengxin"
        / "skills"
        / "scripts"
        / f"{kind}-query.js"
    )
    return p if p.is_file() else None


def _resolve_gaokao_script(kind: str) -> Path | None:
    skill_map = {
        "scores": "tencent-yuanbao-gaokao-regional-passing-scores",
        "rank": "tencent-yuanbao-gaokao-score-to-rank-lookup",
    }
    sub = skill_map.get(kind)
    if not sub:
        return None
    p = (
        _get_workbuddy_home()
        / "plugins"
        / "marketplaces"
        / "cb_teams_marketplace"
        / "plugins"
        / "gaokao-advisor"
        / "skills"
        / sub
        / "fetch_data.py"
    )
    return p if p.is_file() else None


def _resolve_westock_bin() -> Path | None:
    bin_name = "westock.exe" if os.name == "nt" else "westock"
    home = Path.home()
    candidates = [
        home / ".local" / "bin" / bin_name,
        home / ".westock" / "channels" / "wbgeneral" / "bin" / bin_name,
    ]
    for c in candidates:
        if c.is_file():
            return c
    which = shutil.which("westock")
    return Path(which) if which else None


def _resolve_mcp_url(alias: str) -> str:
    meta = MCP_REGISTRY.get(alias)
    if not meta:
        raise ValueError(f"Unknown MCP alias '{alias}'. Choices: {', '.join(sorted(MCP_REGISTRY))}")
    mcp_json = _get_workbuddy_home() / "connectors-marketplace" / "connectors" / meta["dir"] / "mcp.json"
    if mcp_json.is_file():
        try:
            data = json.loads(mcp_json.read_text(encoding="utf-8"))
            servers = data.get("mcpServers", data)
            if isinstance(servers, dict):
                for sdef in servers.values():
                    if isinstance(sdef, dict) and isinstance(sdef.get("url"), str) and sdef["url"].strip():
                        return sdef["url"].strip()
        except Exception:
            pass
    if meta["fallback_url"]:
        return meta["fallback_url"]
    raise FileNotFoundError(f"MCP URL unavailable for '{alias}': {mcp_json}")


def _parse_jsonrpc_response(raw_text: str, expected_id: int) -> dict[str, Any]:
    """Parse Streamable HTTP JSON or SSE payload into the target JSON-RPC object."""
    text = raw_text.strip()
    if not text:
        raise ValueError("Empty HTTP response body")
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
        if isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict) and item.get("id") == expected_id:
                    return item
            if parsed and isinstance(parsed[-1], dict):
                return parsed[-1]
    except json.JSONDecodeError:
        pass

    blocks = re.split(r"\r?\n\r?\n", text)
    candidates: list[dict[str, Any]] = []
    for block in blocks:
        data_lines = [line[5:].lstrip() for line in block.splitlines() if line.startswith("data:")]
        if not data_lines:
            continue
        payload_str = "\n".join(data_lines).strip()
        if not payload_str or payload_str == "[DONE]":
            continue
        try:
            obj = json.loads(payload_str)
            if isinstance(obj, dict):
                if obj.get("id") == expected_id:
                    return obj
                candidates.append(obj)
        except json.JSONDecodeError:
            continue
    if candidates:
        return candidates[-1]
    raise ValueError(f"Unparseable MCP response: {text[:300]}")


def _mcp_post(url: str, payload: dict[str, Any], session_id: str | None = None, timeout: int = 20) -> tuple[str | None, str]:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    if session_id:
        headers["Mcp-Session-Id"] = session_id
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        sid = resp.headers.get("Mcp-Session-Id") or resp.headers.get("mcp-session-id")
        body = resp.read().decode("utf-8", errors="replace")
        return sid, body


def _mcp_session_request(alias: str, method: str, params: dict[str, Any], timeout: int = 25) -> dict[str, Any]:
    """Run MCP initialize handshake followed by a single JSON-RPC method request."""
    url = _resolve_mcp_url(alias)
    init_req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "workbuddy-supplement", "version": "1.0.0"},
        },
    }
    sid, _ = _mcp_post(url, init_req, timeout=timeout)
    try:
        _mcp_post(url, {"jsonrpc": "2.0", "method": "notifications/initialized"}, session_id=sid, timeout=5)
    except Exception:
        pass
    _, body = _mcp_post(url, {"jsonrpc": "2.0", "id": 2, "method": method, "params": params}, session_id=sid, timeout=timeout)
    return _parse_jsonrpc_response(body, expected_id=2)


def _resolve_validated_proxy_url() -> tuple[str | None, int | None, str | None]:
    """Validate WB_FREE_PROXY_URL so only loopback HTTP(S) endpoints are ever allowed."""
    raw = os.environ.get("WB_FREE_PROXY_URL", "http://127.0.0.1:8045").strip() or "http://127.0.0.1:8045"
    parsed = urlparse(raw)
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in ("http", "https") or host not in LOOPBACK_HOSTS:
        return None, None, f"WB_FREE_PROXY_URL must target 127.0.0.1 or localhost (got '{raw}')"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    base = f"{parsed.scheme}://{host}:{port}"
    return base, port, None


def _check_8045_online(timeout: float = 2.0) -> tuple[bool, str]:
    base, _, err = _resolve_validated_proxy_url()
    if err or not base:
        return False, err or "Invalid loopback proxy URL"
    try:
        req = urllib.request.Request(f"{base}/v1/models", method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                return True, "HTTP 200"
            return False, f"HTTP {resp.status}"
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def _pick_8045_model_id() -> str | None:
    _, target_port, err = _resolve_validated_proxy_url()
    if err or target_port is None:
        return None
    models_path = _get_workbuddy_home() / "models.json"
    if not models_path.is_file():
        return None
    data = json.loads(models_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        return None
    local_ids: list[str] = []
    for entry in data:
        if not isinstance(entry, dict):
            continue
        raw_url = str(entry.get("url") or entry.get("baseUrl") or "").strip()
        parsed = urlparse(raw_url)
        host = (parsed.hostname or "").lower()
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        if parsed.scheme in ("http", "https") and host in LOOPBACK_HOSTS and port == target_port and entry.get("id"):
            local_ids.append(str(entry["id"]))
    for pref in PREFERRED_LOCAL_MODELS:
        if pref in local_ids:
            return pref
    return local_ids[0] if local_ids else None


def _run_subprocess(cmd: list[str], extra_env: dict[str, str] | None = None, timeout: int = 120) -> int:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    if extra_env:
        env.update(extra_env)
    proc = subprocess.run(cmd, env=env, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    return proc.returncode


def _parse_scalar_value(val: str) -> Any:
    low = val.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    if low == "null":
        return None
    if re.fullmatch(r"-?\d+", val):
        try:
            return int(val)
        except ValueError:
            pass
    if re.fullmatch(r"-?\d+\.\d+", val):
        try:
            return float(val)
        except ValueError:
            pass
    if (val.startswith("{") and val.endswith("}")) or (val.startswith("[") and val.endswith("]")):
        try:
            return json.loads(val)
        except json.JSONDecodeError:
            pass
    return val


def cmd_doctor(probe: bool) -> int:
    westock_bin = _resolve_westock_bin()
    westock_status: dict[str, Any] = {"installed": bool(westock_bin), "path": str(westock_bin) if westock_bin else None}
    if westock_bin:
        ver_r = subprocess.run([str(westock_bin), "--version"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=8)
        westock_status["version"] = ver_r.stdout.strip() or ver_r.stderr.strip()
        help_r = subprocess.run([str(westock_bin), "--help"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=8)
        if "\n  auth " in help_r.stdout or "\n    auth " in help_r.stdout:
            st_r = subprocess.run([str(westock_bin), "auth", "status"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10)
            out_s = (st_r.stdout or st_r.stderr).strip()
            if out_s.startswith("READY"):
                westock_status["auth"] = "READY"
            elif out_s.startswith("AUTH_REQUIRED:"):
                westock_status["auth"] = "AUTH_REQUIRED"
            else:
                westock_status["auth"] = out_s.split(":", 1)[0] if out_s else "UNKNOWN"
        else:
            westock_status["auth"] = "not_required (channel=workbuddy)" if "channel=workbuddy" in str(westock_status.get("version")) else "no_auth_subcommand"

    online_8045, msg_8045 = _check_8045_online()
    model_8045 = _pick_8045_model_id()
    app_info = _resolve_workbuddy_app()

    report: dict[str, Any] = {
        "workbuddy_home": str(_get_workbuddy_home()),
        "wechat": {"ok": _resolve_wechat_script() is not None, "path": str(_resolve_wechat_script() or "")},
        "travel": {
            "node_ok": shutil.which("node") is not None,
            "scripts": {k: (_resolve_travel_script(k) is not None) for k in TRAVEL_KINDS},
        },
        "gaokao": {k: (_resolve_gaokao_script(k) is not None) for k in GAOKAO_KINDS},
        "westock": westock_status,
        "wb_websearch": {
            "port_8045_online": online_8045,
            "detail": msg_8045,
            "selected_8045_model": model_8045,
            "cli_exists": app_info is not None,
        },
        "mcp_aliases": sorted(MCP_REGISTRY.keys()),
    }
    if probe:
        probes: dict[str, str] = {}
        for alias in ("efunds", "orientfutures"):
            try:
                res = _mcp_session_request(alias, "tools/list", {}, timeout=8)
                tools = res.get("result", {}).get("tools", [])
                probes[alias] = f"OK ({len(tools)} tools)"
            except Exception as exc:
                probes[alias] = f"ERR ({type(exc).__name__}: {exc})"
        report["mcp_probe"] = probes

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def cmd_wechat(args: argparse.Namespace) -> int:
    script = _resolve_wechat_script()
    if not script:
        print("Error: sogou_search.py not found under WorkBuddy plugins directory", file=sys.stderr)
        return 1
    cmd = [sys.executable, str(script)]
    if args.type == "gzh":
        cmd.extend(["--type", "gzh"])
    cmd.append(args.query)
    if args.days is not None:
        cmd.extend(["--days", str(args.days)])
    if args.hours is not None:
        cmd.extend(["--hours", str(args.hours)])
    if args.fetch_content:
        cmd.append("--fetch-content")
    return _run_subprocess(cmd, timeout=90)


def cmd_travel(kind: str, passthrough: list[str]) -> int:
    if kind not in TRAVEL_KINDS:
        print(f"Error: unknown travel kind '{kind}'. Choices: {', '.join(TRAVEL_KINDS)}", file=sys.stderr)
        return 1
    script = _resolve_travel_script(kind)
    if not script:
        print(f"Error: {kind}-query.js not found under tc-chengxin", file=sys.stderr)
        return 1
    return _run_subprocess(["node", str(script), *passthrough], timeout=60)


def cmd_gaokao(kind: str, passthrough: list[str]) -> int:
    if kind not in GAOKAO_KINDS:
        print(f"Error: unknown gaokao kind '{kind}'. Choices: {', '.join(GAOKAO_KINDS)}", file=sys.stderr)
        return 1
    script = _resolve_gaokao_script(kind)
    if not script:
        print(f"Error: gaokao {kind} script not found", file=sys.stderr)
        return 1
    return _run_subprocess([sys.executable, str(script), *passthrough], timeout=60)


def cmd_mcp_tools(alias: str) -> int:
    try:
        res = _mcp_session_request(alias, "tools/list", {}, timeout=20)
    except Exception as exc:
        print(f"Error querying MCP '{alias}': {exc}", file=sys.stderr)
        return 1
    if "error" in res:
        print(json.dumps(res["error"], ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    tools = res.get("result", {}).get("tools", [])
    out = []
    for t in tools:
        schema = t.get("inputSchema") or {}
        out.append(
            {
                "name": t.get("name"),
                "description": t.get("description", ""),
                "required": schema.get("required", []),
                "properties": {
                    k: {kk: v[kk] for kk in ("type", "description", "enum") if kk in v}
                    for k, v in (schema.get("properties") or {}).items()
                },
            }
        )
    print(json.dumps({"alias": alias, "count": len(out), "tools": out}, ensure_ascii=False, indent=2))
    return 0


def cmd_mcp_call(alias: str, tool_name: str, json_arg: str | None, kv_pairs: list[str]) -> int:
    arguments: dict[str, Any] = {}
    if json_arg:
        parsed = json.loads(json_arg)
        if not isinstance(parsed, dict):
            print("Error: --json must decode to a JSON object", file=sys.stderr)
            return 1
        arguments.update(parsed)
    for item in kv_pairs:
        if "=" not in item:
            print(f"Error: invalid argument '{item}', expected key=value or --json", file=sys.stderr)
            return 1
        k, v = item.split("=", 1)
        arguments[k] = _parse_scalar_value(v)

    try:
        res = _mcp_session_request(alias, "tools/call", {"name": tool_name, "arguments": arguments}, timeout=30)
    except Exception as exc:
        print(f"Error calling {alias}.{tool_name}: {exc}", file=sys.stderr)
        return 1
    if "error" in res:
        print(json.dumps(res["error"], ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    result = res.get("result", {})
    content = result.get("content")
    if isinstance(content, list):
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                print(part.get("text", ""))
            else:
                print(json.dumps(part, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result.get("isError") else 0


def cmd_westock(passthrough: list[str]) -> int:
    exe = _resolve_westock_bin()
    if not exe:
        print("Error: westock CLI not found. Run setup script from finance-data/westockdata skill first.", file=sys.stderr)
        return 1
    return _run_subprocess([str(exe), *passthrough], timeout=120)


def cmd_wb_websearch(args: argparse.Namespace) -> int:
    _, _, url_err = _resolve_validated_proxy_url()
    if url_err:
        print(f"[ZERO_COST_GUARD] {url_err}", file=sys.stderr)
        return 2
    online, detail = _check_8045_online()
    if not online:
        print(
            f"[ZERO_COST_GUARD] Local loopback proxy (:8045) is offline ({detail}); refused fallback to paid relays.",
            file=sys.stderr,
        )
        return 2
    model_id = _pick_8045_model_id()
    if not model_id:
        print("[ZERO_COST_GUARD] No model pointing to 127.0.0.1/localhost:8045 found in WorkBuddy models.json.", file=sys.stderr)
        return 2

    app_info = _resolve_workbuddy_app()
    if not app_info:
        print("Error: WorkBuddy CLI assets not found (set WORKBUDDY_APP_DIR if installed elsewhere).", file=sys.stderr)
        return 1
    _, cli_mjs, product_json, launcher = app_info

    constraints = [f'query="{args.query}"']
    if args.freshness:
        constraints.append(f'freshness="{args.freshness}"')
    if args.allowed_domains:
        doms = [d.strip() for d in args.allowed_domains.split(",") if d.strip()]
        constraints.append(f"allowed_domains={json.dumps(doms, ensure_ascii=False)}")
    if args.blocked_domains:
        doms = [d.strip() for d in args.blocked_domains.split(",") if d.strip()]
        constraints.append(f"blocked_domains={json.dumps(doms, ensure_ascii=False)}")

    prompt = (
        f"请立即调用 WebSearch 工具（严格传参：{', '.join(constraints)}），"
        "按原始返回逐条列出标题、URL、发布日期与摘要；若工具报错或无结果，原样报告原因，严禁编造。"
    )
    wb_home = _get_workbuddy_home()
    extra_env = {
        "ELECTRON_RUN_AS_NODE": "1",
        "WORKBUDDY_CONFIG_DIR": str(wb_home),
        "CODEBUDDY_CONFIG_DIR": str(wb_home),
        "ACC_PRODUCT_CONFIG_PATH": str(product_json),
    }
    cmd = [
        *launcher,
        str(cli_mjs),
        "--print",
        "--output-format",
        "json",
        "--no-session-persistence",
        "--permission-mode",
        "bypassPermissions",
        "--model",
        f"custom-local:{model_id}",
        "--tools",
        "WebSearch",
        "--max-turns",
        "3",
        prompt,
    ]
    return _run_subprocess(cmd, extra_env=extra_env, timeout=120)


def cmd_handoff(args: argparse.Namespace) -> int:
    out_path = args.out
    if not out_path:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = str(Path.cwd() / f"workbuddy_{args.kind}_{stamp}.md")

    if args.kind == "domain":
        body = (
            f"{args.topic}\n\n"
            f"请优先使用已连接的官方/金融数据源或 domain_search 完成检索与核验，"
            f"并将带原始来源链接/口径说明的完整结果原样写入文件：`{out_path}`"
        )
    elif args.kind == "corp_legal":
        body = (
            f"请使用同花顺快查（kuaicha-search）、同花顺法律AI（fazhi-law）、"
            f"邓白氏龙易查或企查查/天眼查/北大法宝等已接入连接器查询并核验：{args.topic}\n\n"
            f"将含原始工商/司法/公告出处的结果完整保存至：`{out_path}`"
        )
    else:
        body = (
            f"请调用 knowledge_search（覆盖 ima / 腾讯文档 / 腾讯会议 / 腾讯微云 / 资料库）"
            f"检索与「{args.topic}」相关的全部最新记录与原文片段，"
            f"注明所属文档/来源库并保存至：`{out_path}`"
        )

    print("=== 请将下方指令粘贴到 WorkBuddy 桌面端执行（完成后通知我读取输出文件）===")
    print(body)
    print(f"\n[预期回读路径] {out_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wb_supplement.py",
        description="Zero-cost WorkBuddy vertical info supplement dispatcher.",
    )
    sub = parser.add_subparsers(dest="subcmd", required=True)

    p_doc = sub.add_parser("doctor", help="Check availability of all local WorkBuddy supplement sources")
    p_doc.add_argument("--probe", action="store_true", help="Send read-only initialize+tools/list probe to efunds & orientfutures")

    p_wx = sub.add_parser("wechat", help="Search WeChat official accounts/articles via local sogou_search.py")
    p_wx.add_argument("query", help="Search keyword")
    p_wx.add_argument("--type", choices=("article", "gzh"), default="article")
    p_wx.add_argument("--days", type=int)
    p_wx.add_argument("--hours", type=int)
    p_wx.add_argument("--fetch-content", action="store_true")

    p_tr = sub.add_parser("travel", help="Query Tongcheng real-time travel resources (passthrough flags)")
    p_tr.add_argument("kind", choices=TRAVEL_KINDS)

    p_gk = sub.add_parser("gaokao", help="Query China Gaokao passing scores or score-to-rank (passthrough flags)")
    p_gk.add_argument("kind", choices=GAOKAO_KINDS)

    p_mt = sub.add_parser("mcp-tools", help="List tool schemas for a zero-auth WorkBuddy marketplace MCP")
    p_mt.add_argument("alias", choices=sorted(MCP_REGISTRY))

    p_mc = sub.add_parser("mcp-call", help="Call a tool on a zero-auth WorkBuddy marketplace MCP")
    p_mc.add_argument("alias", choices=sorted(MCP_REGISTRY))
    p_mc.add_argument("tool_name")
    p_mc.add_argument("--json", dest="json_arg", help="JSON object of arguments")
    p_mc.add_argument("kv", nargs="*", help="Optional key=value argument overrides")

    sub.add_parser("westock", help="Invoke official free westock CLI (passthrough flags; do NOT pipe/truncate output)")

    p_ws = sub.add_parser("wb-websearch", help="Zero-cost guarded WorkBuddy WebSearch via loopback :8045 only")
    p_ws.add_argument("query")
    p_ws.add_argument("--freshness", help="d[1-30], m[1-12], or y[1-5]")
    p_ws.add_argument("--allowed-domains", help="Comma-separated allowed domains")
    p_ws.add_argument("--blocked-domains", help="Comma-separated blocked domains")

    p_ho = sub.add_parser("handoff", help="Generate zero-cost copy-paste task prompt for WorkBuddy Desktop")
    p_ho.add_argument("kind", choices=("domain", "corp_legal", "private_kb"))
    p_ho.add_argument("topic")
    p_ho.add_argument("--out", help="Output file path for WorkBuddy to write")

    return parser


def main() -> int:
    parser = build_parser()
    if len(sys.argv) >= 2 and sys.argv[1] == "westock":
        return cmd_westock(sys.argv[2:])
    if len(sys.argv) >= 3 and sys.argv[1] in ("travel", "gaokao"):
        kind = sys.argv[2]
        if kind in ("-h", "--help"):
            parser.parse_args([sys.argv[1], "--help"])
            return 0
        passthrough = sys.argv[3:]
        if sys.argv[1] == "travel":
            return cmd_travel(kind, passthrough)
        return cmd_gaokao(kind, passthrough)

    args = parser.parse_args()
    if args.subcmd == "doctor":
        return cmd_doctor(args.probe)
    if args.subcmd == "wechat":
        return cmd_wechat(args)
    if args.subcmd == "mcp-tools":
        return cmd_mcp_tools(args.alias)
    if args.subcmd == "mcp-call":
        return cmd_mcp_call(args.alias, args.tool_name, args.json_arg, args.kv)
    if args.subcmd == "wb-websearch":
        return cmd_wb_websearch(args)
    if args.subcmd == "handoff":
        return cmd_handoff(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
