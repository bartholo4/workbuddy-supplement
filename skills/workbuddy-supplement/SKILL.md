---
name: workbuddy-supplement
description: >-
  Zero-cost Chinese vertical information supplement backed by local WorkBuddy scripts,
  official free westock CLI, and open MCP endpoints. Use both when the user asks to
  use WorkBuddy's info/research sources and proactively when web search lacks Chinese
  vertical data: WeChat official account articles, A/HK/US/JP/KR stock quotes/financials/
  fund flows/screening, China industry-chain trees & index valuation temperatures,
  real-time China train/flight/hotel/scenery tickets, Gaokao scores/rank lookup,
  mutual fund & futures rules, or preparing a WorkBuddy Desktop handoff for
  host-only sources (domain_search, corporate/legal DBs, Tencent ima/Docs/Meeting).
  Do NOT use for dedicated workspace business DBs, Feishu/Lark, or Google Workspace.
---

# WorkBuddy 零费用信息补充 (`workbuddy-supplement`)

通过本机 [wb_supplement.py](./scripts/wb_supplement.py) 统一调用 WorkBuddy 盘上可免成本获取的垂类信息源。**对 WorkBuddy 安装目录与 `~/.workbuddy` 全程只读，严禁读取或打印 Token/Key/Ticket，严禁回退任何收费中转模型。**

## 1. 路由表（按需直接调用）

| 需求类型 | 推荐命令（经 `wb_supplement.py`） | 费用/前提 |
|---|---|---|
| **A/港/美/日韩股行情、财报、资金流、龙虎榜、研报、宏观、产业链、选股/选基** | `westock <子命令> [参数]` | 免费官方 CLI（`channel=workbuddy` 免额外登录；勿管道截断输出，代码带市场前缀如 `sh600519`/`hk00700`/`usAAPL`） |
| **微信公众号文章 / 公众号检索与正文** | `wechat "关键词" [--days 7] [--fetch-content]` / `--type gzh` | 免费公网抓取（遇搜狗验证码立即停止如实报告） |
| **国内实时高铁/火车、机票/低价、酒店、景区门票、大巴** | `travel <train\|flight\|hotel\|scenery\|bus\|traffic\|travel> [参数]` | 免费直调 `tc-chengxin` |
| **全国各省高考分数线 / 一分一段位次** | `gaokao scores ...` / `gaokao rank ...` | 免费公开接口（勿调用需内网 Token 的 `gaokao-search.py`） |
| **A 股产业链节点树、成分股/Wind指数详情与估值温度、易方达基金、东证期货规则、24好玩等开放 MCP** | `mcp-tools <alias>` → `mcp-call <alias> <tool> [k=v]` | 免费匿名 HTTP MCP（`efunds` / `orientfutures` / `24haowan` / `lingyi` / `mindbye`） |
| **带 `d1-d30` 精确时间窗/域名黑白名单的 WorkBuddy `WebSearch`** | `wb-websearch "query" [--freshness d7] [--allowed-domains ...]` | **仅当本机环回 `:8045` 在线时启用**；离线返回退出码 `2` 并阻止调用付费中转 |
| **WorkBuddy 桌面端独占能力**（`domain_search`、非上市企业工商/司法库、腾讯 `ima`/腾讯文档/腾讯会议私域） | `handoff <domain\|corp_legal\|private_kb> "目标"` | 生成一段可直接粘贴到 WorkBuddy 桌面端的任务指令，由用户运行并落盘后回读 |
| **健康自检** | `doctor [--probe]` | 检查各脚本、`westock` 状态、`:8045` 与 MCP 连通性 |

## 2. 执行命令

定位与当前 `SKILL.md` 同级的 `scripts/wb_supplement.py` 执行（Windows UTF-8 已内置兼容）：

```bash
python "<path-to-skill>/scripts/wb_supplement.py" <subcommand> ...
```

### 关键纪律
1. **`westock` 口径与防猜**：
   - 先用 `westock search <名称>` 查代码再传带市场前缀的代码；不确定的子命令先执行 `westock <subcmd> --help` 确认参数（例如 `v0.0.4` 中 `finance` 使用 `--type income|balance|cashflow`）。
   - **禁止**对 `westock` 输出加 `| grep` / `| head` 截断；直接阅读返回的 Markdown 表格。
   - 若所用渠道返回 `AUTH_REQUIRED:<url>`，向用户展示链接后启动 `westock auth fetch --wait 300` 等待微信扫码，勿循环轮询 `auth status`。
2. **开放 MCP 先看 Schema 再传参**：首次用某个 tool 前先跑 `mcp-tools <alias>` 或查阅 [free-sources-guide.md](./references/free-sources-guide.md)，避免参数名或枚举值错误。
3. **`wb-websearch` 零费用门禁**：内置强制检查本地环回代理（默认 `http://127.0.0.1:8045/v1/models`，即使设置 `WB_FREE_PROXY_URL` 也只允许 `127.0.0.1`/`localhost`）且校验 `~/.workbuddy/models.json` 所选模型指向同一环回端口；未启动或校验不通过时返回退出码 `2`，改用常规检索或 `handoff` 代替。
4. **桌面接力 (`handoff`) 约束**：生成 `domain` 类型指令时保持单句研究意图（不拆字段清单），交由 WorkBuddy 桌面端调用 `domain_search` / `server-side` 连接器 / `knowledge_search` 并把结果写入指定路径文件后再读取。
5. **路由排他边界**：专用工作区业务库、飞书及 Google Workspace 等已有原生专用集成的场景，仍走各自专用技能或工具。

## 3. 更多工具详情

完整工具列表、参数示例与 `westock` / `travel` / `gaokao` / `efunds` / `orientfutures` 用法见 [free-sources-guide.md](./references/free-sources-guide.md)。
