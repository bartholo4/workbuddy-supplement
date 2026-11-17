# workbuddy-supplement

[English](README.en.md)

面向 AI 编码智能体（Antigravity / Codex / Claude Code 等）的**零额外费用中国垂类信息补充技能**。以只读、无侵入的方式复用本机已安装的腾讯 [WorkBuddy](https://www.workbuddy.cn/) 周边脚本、官方免费 `westock` CLI 与免鉴权开放 MCP 接口，补齐通用公网检索在中文垂类数据上的空白。

- **按需渐进加载，无常驻进程**：支持用户显式点名调用，或当常规联网搜索缺少国内垂类数据时自动触发。
- **严守零费用门禁**：数据查询全部直连免费接口，不经过付费模型；唯一涉及推理层的无头 `wb-websearch` 硬绑定本地环回 `:8045` 代理并校验 `models.json`，离线即返回退出码 `2` 拒绝降级付费中转。
- **不绑定 WorkBuddy 单一版本，不分发第三方二进制**：仅包含原装 `SKILL.md`、调度脚本与安装器，全程对 `WorkBuddy` 安装目录与 `~/.workbuddy` 只读。

## 能力矩阵

| 层级 | 能力与入口 | 前置条件 |
|---|---|---|
| **免费官方金融 CLI** | `westock`：A/港/美/日韩股行情、三大财报、资金流向、龙虎榜、宏观、产业链、条件/评分选股与选基 | 本地已安装官方免费 `westock` CLI（`channel=workbuddy` 免额外登录；若使用需鉴权渠道则按提示扫码） |
| **本地免登录脚本** | ① `wechat`：微信公众号与最新文章全文（调用 `sogou_search.py`）<br>② `travel`：同程实时高铁/机票/低价/酒店/景区/大巴<br>③ `gaokao`：各省历年高考分数线与一分一段位次（直连公开 `gaokao.search.qq.com`） | 本地 `~/.workbuddy` 插件/连接器市场缓存存在对应脚本 |
| **免鉴权开放 MCP** | `efunds`（易方达基金与 23 条 A 股产业链/Wind 指数温度，18 工具）、`orientfutures`（东证期货审核知识库，5 工具）、`24haowan`、`lingyi`、`mindbye`、`chainlon-geo`、`hefei-alerts` | 仅需联网，核心别名内置硬编码兜底 URL |
| **安全无头 `WebSearch`** | `wb-websearch`：调用 WorkBuddy CLI 的 `WebSearch`（支持 `d1-d30` 时间窗与域名过滤） | 仅当本机环回 `:8045`（可用 `WB_FREE_PROXY_URL` 覆盖但仅限 `127.0.0.1`/`localhost`）在线且 `models.json` 存在指向该端口的模型时放行 |
| **桌面独占能力接力** | `handoff`：生成可粘贴进 WorkBuddy 桌面端的单句研究指令并约定落盘回读路径（`domain_search`、企业工商司法库、腾讯 `ima`/文档/会议私域） | 用户已登录 WorkBuddy 桌面端时按需粘贴运行 |

## 快速安装

要求 **Python 3.10+**（可选需要同程脚本时准备 **Node.js 18+**）。脚本自动按默认目标安装并执行 `doctor` 自检：

```bash
# 安装到 Antigravity 全局技能目录 (~/.gemini/config/skills/workbuddy-supplement)
python scripts/install.py

# 或安装到 Codex / Claude Code / 自定义目录
python scripts/install.py --target codex
python scripts/install.py --target claude
python scripts/install.py --target custom --dest /path/to/skills/workbuddy-supplement

# 检查与卸载
python scripts/install.py --check
python scripts/install.py --uninstall
```

## 常用命令示例

```bash
python skills/workbuddy-supplement/scripts/wb_supplement.py doctor --probe
python skills/workbuddy-supplement/scripts/wb_supplement.py wechat "人工智能" --days 7
python skills/workbuddy-supplement/scripts/wb_supplement.py travel train --departure "北京" --destination "上海" --extra "明天 高铁"
python skills/workbuddy-supplement/scripts/wb_supplement.py gaokao scores --place 福建 --year 2024 --student 物理
python skills/workbuddy-supplement/scripts/wb_supplement.py gaokao rank --place 福建 --classify 物理 --score 600
python skills/workbuddy-supplement/scripts/wb_supplement.py mcp-tools efunds
python skills/workbuddy-supplement/scripts/wb_supplement.py mcp-call efunds industry_chain_query_node chain_name=芯片
python skills/workbuddy-supplement/scripts/wb_supplement.py westock quote sh600519
python skills/workbuddy-supplement/scripts/wb_supplement.py handoff domain "研究 A 股贵州茅台（600519）的整体情况"
```

可通过环境变量调整发现位置：

- `WORKBUDDY_CONFIG_DIR`：覆盖 WorkBuddy 用户数据目录（默认 `~/.workbuddy`）。
- `WORKBUDDY_APP_DIR`：覆盖 WorkBuddy 主程序安装目录（默认按系统自动探测）。
- `WB_FREE_PROXY_URL`：覆盖本地免费代理地址（默认 `http://127.0.0.1:8045`，仅允许 `127.0.0.1` 或 `localhost`）。

## 升级稳定性

- 独立 CLI（`westock`）与内置兜底 URL 的公开 MCP 不受 WorkBuddy 客户端版本升级影响。
- `sogou_search.py` 按缓存版本号降序通配解析，插件升级自动切换最新版。
- 仅 `wb-websearch` 依赖 WorkBuddy 主程序内部 CLI 路径与参数；每次客户端大版本更新后运行 `doctor --probe` 即可立即定位受影响通道。

## 自测

```bash
python -m unittest discover -s tests -v
```

## 许可与免责声明

本项目按 [MIT License](LICENSE) 开源；与腾讯官方或任何数据源厂商不存在隶属或背书关系。详细第三方组件声明见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
