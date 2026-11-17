# Free Sources Reference (`workbuddy-supplement`)

All commands below invoke `scripts/wb_supplement.py` alongside `SKILL.md` with zero LLM/API charges.

---

## 1. 腾讯自选股 CLI (`westock`)

- **Binary**: `~/.local/bin/westock` (`westock.exe` on Windows; tested on `westock 0.0.4 channel=workbuddy`, works without extra login on that channel).
- **Invoke via**: `python "<path-to-skill>/scripts/wb_supplement.py" westock <subcommand> [flags]`
- **WorkBuddy reference docs** (when `finance-data` plugin is cached locally under `~/.workbuddy/plugins/cache/cb_teams_marketplace/finance-data/`):
  - Consult `skills/westock-data/SKILL.md`, `references/commands.md`, and `skills/westock-screener/SKILL.md` if present.
- **Core rules**:
  1. Always run `westock <subcmd> --help` first when a subcommand's flags are uncertain (`v0.0.4` vs newer docs may differ; e.g., `westock finance` uses `--type income|balance|cashflow`).
  2. Never pipe (`|`) or truncate `westock` stdout/stderr; read the returned Markdown table directly.
  3. Include market prefix on codes (`sh600519`, `sz300750`, `hk00700`, `usAAPL`). Unknown codes -> run `westock search <关键词>` first.
  4. If using a channel requiring QR auth (`AUTH_REQUIRED:<url>`), present the URL once and run `westock auth fetch --wait 300` instead of looping `auth status`.

Verified commands:
```bash
python "<path-to-skill>/scripts/wb_supplement.py" westock quote sh600519
python "<path-to-skill>/scripts/wb_supplement.py" westock finance sh600036 --type income --limit 1
python "<path-to-skill>/scripts/wb_supplement.py" westock screen ranking --type CompScore --limit 10
python "<path-to-skill>/scripts/wb_supplement.py" westock macro list
```

---

## 2. 微信公众号 (`wechat` / `sogou_search.py`)

```bash
python "<path-to-skill>/scripts/wb_supplement.py" wechat "关键词" [--days 7 | --hours 24] [--fetch-content]
python "<path-to-skill>/scripts/wb_supplement.py" wechat "公众号名" --type gzh
```

- Returns JSON + summary from public `weixin.sogou.com`.
- Temporary jump links expire after a few hours; avoid rapid bursts to reduce Sogou CAPTCHA triggers (on CAPTCHA/anti-bot block, stop and report).

---

## 3. 实时交通与酒旅 (`travel` / `tc-chengxin`)

Available subcommands: `train`, `flight`, `hotel`, `scenery`, `bus`, `traffic`, `travel`.

Verified examples & flags:
```bash
python "<path-to-skill>/scripts/wb_supplement.py" travel train --departure "北京" --destination "上海" --extra "明天 高铁"
python "<path-to-skill>/scripts/wb_supplement.py" travel train --train-number "G1"
python "<path-to-skill>/scripts/wb_supplement.py" travel flight --departure "北京" --destination "上海" --low-price --extra "明天"
python "<path-to-skill>/scripts/wb_supplement.py" travel hotel --destination "上海" --extra "外滩附近 明天入住"
python "<path-to-skill>/scripts/wb_supplement.py" travel scenery --destination "杭州" --extra "适合亲子"
```

---

## 4. 中国高考分数线与位次 (`gaokao`)

Only uses the two public `gaokao.search.qq.com` endpoints (`scores` and `rank`; does **not** call `gaokao-search.py` which requires an internal WorkBuddy token).

```bash
python "<path-to-skill>/scripts/wb_supplement.py" gaokao scores --place 福建 --year 2024 2023 --student 物理 历史
python "<path-to-skill>/scripts/wb_supplement.py" gaokao rank --place 福建 --year 2024 --classify 物理 --score 600
python "<path-to-skill>/scripts/wb_supplement.py" gaokao rank --place 福建 --year 2024 --classify 物理 --rank 10000
```

---

## 5. 免鉴权开放 MCP (`mcp-tools` / `mcp-call`)

Inspect live schema anytime: `python "<path-to-skill>/scripts/wb_supplement.py" mcp-tools <alias>`

### `efunds` (18 tools — 易方达基金与产业链/Wind指数库)
- **产业链与指数估值**:
  - `industry_chain_query_node` (`chain_name` required, exact match — known valid chains: `建筑材料`、`军工`、`绿色电力`、`人工智能`、`装备产业`、`石化`、`消费`、`消费电子`、`芯片`、`物联网`、`现代农业`、`软件`、`新能源`、`碳中和`、`云计算`、`医药`、`汽车零部件`、`智能电车`、`储能电池`、`信息安全`、`机器人`、`建材`、`化工`；注意用 `芯片` 而非 `半导体`)
  - `industry_chain_get_node_index` (`node_id`), `industry_chain_get_node_definition` (`node_id`)
  - `industry_chain_get_node_stock` (`node_id`), `industry_chain_get_stock_detail` (`stock_code`, opt `chain_name`)
  - `industry_chain_query_node_article` (`node_id`, `type`: `news` | `announce`, opt `beg_num`, `fetch_num`)
  - `industry_chain_get_news_content` (`news_id`)
  - `industry_chain_get_index_info` (`index_code`), `industry_chain_query_temperature_by_index` (`index_code`), `industry_chain_query_index_fund` (`index_code`)
  - `industry_chain_get_node_etf` (`node_id`), `industry_chain_query_etf_trade` (`fund_code`), `industry_chain_query_stock_fund` (`stock_code`), `industry_chain_query_stock_trade` (`stock_code`)
- **易方达基金画像与筛选**:
  - `fund_profile_query` (`fund_code` 6-digit string with leading zeros, opt `modules` array)
  - `fund_metric_screen` (`metric`: `return` | `max_drawdown`, `period`: `1m`|`3m`|`6m`|`1y`|`ytd`|`3y`|`5y`|`inception`, opt `operator`, `value`, `value_max`, `sort_order`, `limit`)
  - `search_wx_articles` (opt `keyword` array, `account`, `title`, `start_date`, `end_date`), `get_wx_article_detail` (`article_id`)

### `orientfutures` (5 tools — 东证期货审核知识库)
- `knowledge_base_list_books` (no args -> list `book_key` collections)
- `knowledge_base_get_book_toc` (`book_key` required, opt `root`, `depth`)
- `knowledge_base_get_section_content` (`book_key`, `section` required, opt `view`: `subtree` | `self`, `max_bytes`)
- `business_links_show`, `knowledge_visual_compose`

### Other verified zero-auth aliases
- `mindbye` (3 tools): `contract_review_submit`, `contract_review_result`, `contract_review_prepare_upload`
- `lingyi` (1 tool): `open_lingyi_skill` (`skill_id`)
- `24haowan` (8 tools): `search_templates`, `get_template`, `list_cases`, `get_case`, `search_knowledge`, `list_industries`, `get_industry_benchmark`, `get_player_behavior`
- Additional registered aliases (run `mcp-tools <alias>` before calling): `chainlon-geo`, `hefei-alerts`
