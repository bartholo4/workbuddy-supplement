# workbuddy-supplement

[中文说明](README.md)

A **zero-extra-cost Chinese vertical information supplement skill** for AI coding agents (Antigravity, Codex, Claude Code, etc.). It provides read-only, non-invasive orchestration over existing local WorkBuddy scripts, the official free `westock` CLI, and public HTTP MCP services to fill gaps left by general global web search.

- **Progressive on-demand loading**: triggers when explicitly requested or automatically when web search lacks Chinese vertical sources, with no background daemon.
- **Strict Zero-Cost Guard**: structured vertical lookups bypass external LLMs entirely; headless `wb-websearch` enforces a hard loopback-only check (`127.0.0.1`/`localhost:8045` online + matching `models.json` entry) and aborts with exit code `2` rather than falling back to paid relays.
- **Version-resilient & zero binary redistribution**: ships only original skill docs, Python standard-library scripts, an installer, and offline tests under MIT; never modifies WorkBuddy files or reads/prints secrets.

## Capability Layers

| Layer | Coverage & Entry | Prerequisites |
|---|---|---|
| **Official Free Stock CLI** | `westock`: A-share / HK / US / JP / KR quotes, financial statements, capital flows, macro indicators, industry chains, and multi-factor screening | Official free `westock` CLI installed locally (`channel=workbuddy` works without extra sign-in; QR-gated channels prompt on demand) |
| **Local Zero-Auth Scripts** | 1. `wechat`: WeChat official accounts & article full text (`sogou_search.py`)<br>2. `travel`: Real-time China rail/flight/hotel/scenery/bus (`tc-chengxin`)<br>3. `gaokao`: Provincial cutoff lines & score-to-rank (`gaokao.search.qq.com`) | Corresponding WorkBuddy marketplace/plugin cache present under `WORKBUDDY_CONFIG_DIR` (`~/.workbuddy`) |
| **Public Zero-Auth MCPs** | `efunds` (18 tools: mutual fund profiles/screening, 23 A-share industry chains & Wind index temperatures), `orientfutures` (5 tools: futures knowledge base), `24haowan`, `lingyi`, `mindbye`, `chainlon-geo`, `hefei-alerts` | Network access; core aliases include built-in fallback URLs |
| **Guarded Headless `WebSearch`** | `wb-websearch`: WorkBuddy CLI `WebSearch` with `d1-d30` freshness and domain allow/block lists | Only runs when loopback `:8045` responds HTTP 200 and `models.json` routes a custom model to that loopback port |
| **Desktop Handoff** | `handoff`: generates concise prompts with output file paths for WorkBuddy Desktop-exclusive features (`domain_search`, enterprise/legal DBs, private `ima`/Docs/Meeting) | Logged-in WorkBuddy Desktop session |

## Quick Install

Requires **Python 3.10+** (plus **Node.js 18+** if using Tongcheng travel scripts).

```bash
# Install to Antigravity (~/.gemini/config/skills/workbuddy-supplement) and verify
python scripts/install.py

# Or target Codex / Claude Code / a custom directory
python scripts/install.py --target codex
python scripts/install.py --target claude
python scripts/install.py --target custom --dest /path/to/skills/workbuddy-supplement

# Verify or remove
python scripts/install.py --check
python scripts/install.py --uninstall
```

## Examples

```bash
python skills/workbuddy-supplement/scripts/wb_supplement.py doctor --probe
python skills/workbuddy-supplement/scripts/wb_supplement.py wechat "AI" --days 7
python skills/workbuddy-supplement/scripts/wb_supplement.py travel train --departure "北京" --destination "上海" --extra "明天 高铁"
python skills/workbuddy-supplement/scripts/wb_supplement.py gaokao scores --place 福建 --year 2024 --student 物理
python skills/workbuddy-supplement/scripts/wb_supplement.py mcp-tools efunds
python skills/workbuddy-supplement/scripts/wb_supplement.py mcp-call efunds industry_chain_query_node chain_name=芯片
python skills/workbuddy-supplement/scripts/wb_supplement.py westock quote sh600519
python skills/workbuddy-supplement/scripts/wb_supplement.py handoff domain "研究 A 股贵州茅台（600519）的整体情况"
```

Optional environment overrides:

- `WORKBUDDY_CONFIG_DIR`: override WorkBuddy config root (default `~/.workbuddy`).
- `WORKBUDDY_APP_DIR`: override WorkBuddy app installation directory.
- `WB_FREE_PROXY_URL`: override loopback proxy URL (default `http://127.0.0.1:8045`; strictly restricted to `127.0.0.1` or `localhost`).

## Testing

```bash
python -m unittest discover -s tests -v
```

## License & Disclaimer

Licensed under the [MIT License](LICENSE). Independent tooling not affiliated with or endorsed by Tencent or upstream data providers; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
