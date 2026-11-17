# Third-Party Notices

This repository contains only original skill definitions, documentation, an
installer script, tests, and a thin Python standard-library dispatcher under the
[MIT License](LICENSE).

It **does not** bundle, mirror, or redistribute any proprietary binaries,
desktop applications, plugin archives, or credentials from Tencent WorkBuddy or
any external data provider. Users supply or invoke those tools from their own
environment under each provider's respective terms:

- **WorkBuddy** (Tencent): local desktop host, bundled CLI runtime, and built-in
  marketplace plugin caches referenced read-only at runtime. Not affiliated with
  or endorsed by Tencent.
- **WeStock CLI (`westock`)** (Tencent Stock / 自选股团队): invoked as an
  external user-installed CLI binary when present on the host.
- **Tongcheng Travel (`tc-chengxin`)**: local Node query scripts inside the
  user's WorkBuddy marketplace cache, invoked read-only when installed.
- **WeChat Article Search (`sogou_search.py`)**: part of the `deep-research`
  plugin in `cb_teams_marketplace` (MIT licensed upstream); invoked read-only
  when installed locally.
- **Public HTTP MCP / Open Endpoints**: `efunds` (易方达基金), `orientfutures`
  (东证期货), `24haowan`, `lingyi`, `mindbye`, `chainlon-geo`, `hefei-alerts`,
  and public Gaokao score endpoints (`gaokao.search.qq.com`). Availability and
  usage remain subject to each upstream service's public terms.
