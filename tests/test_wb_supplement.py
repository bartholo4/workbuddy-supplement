#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Offline unit and repository hygiene tests for workbuddy-supplement."""

from __future__ import annotations

import argparse
import importlib.util
import io
import json
import os
import re
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent
WB_SCRIPT = REPO_ROOT / "skills" / "workbuddy-supplement" / "scripts" / "wb_supplement.py"
INSTALL_SCRIPT = REPO_ROOT / "scripts" / "install.py"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


wb = _load_module("wb_supplement", WB_SCRIPT)
installer = _load_module("install", INSTALL_SCRIPT)


class ParseJsonRpcTests(unittest.TestCase):
    def test_plain_json_dict(self) -> None:
        res = wb._parse_jsonrpc_response('{"jsonrpc":"2.0","id":2,"result":{"ok":true}}', expected_id=2)
        self.assertEqual(res["id"], 2)
        self.assertTrue(res["result"]["ok"])

    def test_json_batch_list_selects_expected_id(self) -> None:
        payload = json.dumps([
            {"jsonrpc": "2.0", "id": 1, "result": "first"},
            {"jsonrpc": "2.0", "id": 2, "result": "second"},
        ])
        res = wb._parse_jsonrpc_response(payload, expected_id=2)
        self.assertEqual(res["result"], "second")

    def test_single_sse_frame(self) -> None:
        raw = 'event: message\ndata: {"jsonrpc":"2.0","id":2,"result":{"tools":["a"]}}\n\n'
        res = wb._parse_jsonrpc_response(raw, expected_id=2)
        self.assertEqual(res["result"]["tools"], ["a"])

    def test_multi_frame_sse_with_notifications_and_done(self) -> None:
        raw = (
            'event: message\n'
            'data: {"jsonrpc":"2.0","method":"notifications/progress","params":{"p":50}}\n\n'
            'event: message\n'
            'data: {"jsonrpc":"2.0","id":2,"result":{"items":[1,2,3]}}\n\n'
            'data: [DONE]\n\n'
        )
        res = wb._parse_jsonrpc_response(raw, expected_id=2)
        self.assertEqual(res["id"], 2)
        self.assertEqual(res["result"]["items"], [1, 2, 3])


class PathAndConfigResolutionTests(unittest.TestCase):
    def test_resolve_wechat_script_prefers_highest_cache_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            for ver in ("1.0.0", "1.2.0"):
                p = base / "plugins" / "cache" / "cb_teams_marketplace" / "deep-research" / ver / "skills" / "wechat-article-search" / "scripts"
                p.mkdir(parents=True)
                (p / "sogou_search.py").write_text("# stub\n", encoding="utf-8")
            with mock.patch.dict(os.environ, {"WORKBUDDY_CONFIG_DIR": tmp}):
                chosen = wb._resolve_wechat_script()
            self.assertIsNotNone(chosen)
            self.assertIn("1.2.0", str(chosen))

    def test_resolve_wechat_script_falls_back_to_marketplace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fb = Path(tmp) / "plugins" / "marketplaces" / "cb_teams_marketplace" / "plugins" / "deep-research" / "skills" / "wechat-article-search" / "scripts"
            fb.mkdir(parents=True)
            target = fb / "sogou_search.py"
            target.write_text("# fallback\n", encoding="utf-8")
            with mock.patch.dict(os.environ, {"WORKBUDDY_CONFIG_DIR": tmp}):
                chosen = wb._resolve_wechat_script()
            self.assertEqual(chosen, target)

    def test_resolve_mcp_url_custom_and_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mpath = Path(tmp) / "connectors-marketplace" / "connectors" / "efunds"
            mpath.mkdir(parents=True)
            (mpath / "mcp.json").write_text(
                json.dumps({"mcpServers": {"efunds": {"url": "https://custom.example.invalid/mcp"}}}),
                encoding="utf-8",
            )
            with mock.patch.dict(os.environ, {"WORKBUDDY_CONFIG_DIR": tmp}):
                self.assertEqual(wb._resolve_mcp_url("efunds"), "https://custom.example.invalid/mcp")
                self.assertEqual(
                    wb._resolve_mcp_url("orientfutures"),
                    "https://commosmart.orientfutures.com/mcp/knowledge-base",
                )


class ZeroCostGuardTests(unittest.TestCase):
    def _make_ws_args(self) -> argparse.Namespace:
        return argparse.Namespace(query="test", freshness=None, allowed_domains=None, blocked_domains=None)

    def test_rejects_offline_loopback_proxy(self) -> None:
        with mock.patch.object(wb, "_check_8045_online", return_value=(False, "ConnectionRefused")):
            err = io.StringIO()
            with redirect_stderr(err):
                rc = wb.cmd_wb_websearch(self._make_ws_args())
        self.assertEqual(rc, 2)
        self.assertIn("[ZERO_COST_GUARD]", err.getvalue())

    def test_rejects_paid_remote_models_even_if_proxy_online(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "models.json").write_text(
                json.dumps([{"id": "paid-only", "url": "https://paid-relay.example.invalid/v1"}]),
                encoding="utf-8",
            )
            with (
                mock.patch.dict(os.environ, {"WORKBUDDY_CONFIG_DIR": tmp, "WB_FREE_PROXY_URL": "http://127.0.0.1:8045"}),
                mock.patch.object(wb, "_check_8045_online", return_value=(True, "HTTP 200")),
            ):
                err = io.StringIO()
                with redirect_stderr(err):
                    rc = wb.cmd_wb_websearch(self._make_ws_args())
        self.assertEqual(rc, 2)
        self.assertIn("[ZERO_COST_GUARD]", err.getvalue())

    def test_rejects_non_loopback_proxy_env_override(self) -> None:
        with mock.patch.dict(os.environ, {"WB_FREE_PROXY_URL": "https://remote-relay.example.invalid:8045"}):
            err = io.StringIO()
            with redirect_stderr(err):
                rc = wb.cmd_wb_websearch(self._make_ws_args())
        self.assertEqual(rc, 2)
        self.assertIn("[ZERO_COST_GUARD]", err.getvalue())


class DoctorAndHandoffTests(unittest.TestCase):
    def test_doctor_empty_config_dir_returns_valid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = io.StringIO()
            with (
                mock.patch.dict(os.environ, {"WORKBUDDY_CONFIG_DIR": tmp}),
                mock.patch.object(wb, "_resolve_westock_bin", return_value=None),
                mock.patch.object(wb, "_resolve_workbuddy_app", return_value=None),
                mock.patch.object(wb, "_check_8045_online", return_value=(False, "offline-mock")),
                redirect_stdout(out),
            ):
                rc = wb.cmd_doctor(probe=False)
        self.assertEqual(rc, 0)
        data = json.loads(out.getvalue())
        self.assertFalse(data["wechat"]["ok"])
        self.assertFalse(data["westock"]["installed"])
        self.assertIn("efunds", data["mcp_aliases"])

    def test_handoff_modes_include_output_path(self) -> None:
        for kind in ("domain", "corp_legal", "private_kb"):
            out = io.StringIO()
            args = argparse.Namespace(kind=kind, topic="样本检索主题", out="/tmp/out_report.md")
            with redirect_stdout(out):
                rc = wb.cmd_handoff(args)
            self.assertEqual(rc, 0)
            text = out.getvalue()
            self.assertIn("/tmp/out_report.md", text)
            self.assertIn("样本检索主题", text)


class InstallerTests(unittest.TestCase):
    def test_install_check_and_uninstall_custom_dest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "custom-skill"
            with redirect_stdout(io.StringIO()):
                self.assertEqual(installer.install_skill(dest), 0)
                self.assertEqual(installer.check_skill(dest, run_doctor=False), 0)
            self.assertTrue((dest / "SKILL.md").is_file())
            self.assertTrue((dest / "scripts" / "wb_supplement.py").is_file())
            self.assertTrue((dest / "references" / "free-sources-guide.md").is_file())
            with redirect_stdout(io.StringIO()):
                self.assertEqual(installer.uninstall_skill(dest), 0)
            self.assertFalse(dest.exists())


class RepoHygieneTests(unittest.TestCase):
    FORBIDDEN_PATTERNS = (
        re.compile(r"[A-Za-z]:\\Users\\"),
        re.compile(r"/Users/(?!username\b)[A-Za-z0-9._-]+"),
        re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9]{20,})\b"),
        re.compile(r"Bearer\s+[A-Za-z0-9._\-]{16,}"),
    )

    def test_lf_endings_and_no_secrets_or_user_paths(self) -> None:
        for path in REPO_ROOT.rglob("*"):
            if ".git" in path.parts or "__pycache__" in path.parts or not path.is_file():
                continue
            raw = path.read_bytes()
            self.assertNotIn(b"\r\n", raw, f"CRLF found in {path.relative_to(REPO_ROOT)}")
            text = raw.decode("utf-8")
            for pat in self.FORBIDDEN_PATTERNS:
                self.assertIsNone(
                    pat.search(text),
                    f"Forbidden pattern {pat.pattern!r} matched in {path.relative_to(REPO_ROOT)}",
                )


if __name__ == "__main__":
    unittest.main()
