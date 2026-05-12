# 开发进度文档
**更新时间**: 2026-05-12  
**当前项目目标**: A股分析可信度审计收口（冲突误报清理 + 结果一致性提升 + 本地聚合 API 配置可诊断性）

---

## 当前开发进度

- New API/One API 等 OpenAI 兼容测试在 Docker 内访问 `localhost` 失败时，会提示改用 `host.docker.internal` 或同网络容器名，避免把 Docker loopback 问题误判成 API Key 问题。
- `docker-compose.local.yml` 与 `docker-compose.yml` 已新增 `new-api` 服务并接入 `tradingagents-network`；默认服务名即 `new-api`，项目内厂家配置应使用 `http://new-api:3000/v1`。
- `PRICE_CONFLICT` 假阳性已继续收口：当前价抽取改为严格锚点（当前价/当前价格/当前股价/现价/最新价），并过滤 `%` 上下文。
- `cn_fact_snapshot` 新增严格版市场报告现价提取入口，避免“位置百分比/指标描述”污染快照现价。
- 跨源冲突判定新增字段级归一化：百分比字段统一口径；金额字段加入万元/百万元/亿元尺度对齐比较，降低单位差异带来的假冲突。

## 最近改了什么（新增）

### 2026-05-12
5. `docker-compose.local.yml` / `docker-compose.yml`
   - 新增 `new-api` 服务，默认镜像 `calciumion/new-api:latest`，容器名固定为 `new-api`。
   - 接入 `tradingagents-network`，并保留宿主机映射 `3000:3000`。
   - 新增 `newapi_data` 数据卷，避免 New API 容器重建后数据直接丢失。
6. `.env.docker`
   - `ONEAPI_BASE_URL` 默认值改为 `http://new-api:3000/v1`，并补充同网络部署说明。
7. `scripts/redeploy.bat`
   - dev 模式服务总数从 `4` 调整为 `5`，prod 模式从 `6` 调整为 `7`，避免新增 `new-api` 后重部署进度统计失真。

## 下一步从哪接着做

- 执行 `scripts\redeploy.bat --dev` 或等价 `docker compose -f docker-compose.local.yml up -d`，让 `new-api` 进入 `tradingagents-network`。
- 进入配置页把 `New API` 的 Base URL 改为 `http://new-api:3000/v1` 后重新点“测试”。
- 若你的实际镜像名不是 `calciumion/new-api:latest`，在启动前设置环境变量 `NEWAPI_IMAGE=<你的镜像名>` 覆盖默认值。
- 冲突判定再收口：仅在“报告期可比”时触发跨源冲突，避免季度/年度或未知期的硬冲突误报。

---

## 最近改了什么（仅保留最近3天）

### 2026-05-12
1. `tradingagents/graph/report_audit.py`
   - `_detect_price_conflict()` 与 `_role_price_conflicts_with_snapshot()` 改用 `_extract_strict_current_prices()`。
   - 新增 `_extract_strict_current_prices()`，只提取显式当前价并过滤百分比上下文。
2. `tradingagents/graph/cn_fact_snapshot.py`
   - `build_cn_fact_snapshot()` 改用 `_extract_market_report_current_price_strict()`。
   - 新增严格提取函数，规避 `12%/59.2%/MA60` 等误提取。
3. `tradingagents/dataflows/china_fundamental_snapshot.py`
   - 新增 `_values_conflict_by_field()`、`_normalize_percent_value()`、`_scaled_relative_diff()`。
   - 冲突判定从通用 `_values_conflict()` 切到字段感知版本，先做口径归一化再判冲突。
4. `tests/test_cn_analysis_trust_audit.py`
   - 新增 `test_price_conflict_ignores_percentage_and_indicator_context` 回归用例。
5. `tradingagents/dataflows/china_fundamental_snapshot.py`
   - 新增 `_report_period_conflict_comparable()`。
   - 冲突计算改为 source+value+report_period 三元信息，报告期不可比时跳过冲突判断。
6. `tests/test_cn_financial_field_supplement.py`
   - 新增 `test_conflict_detection_skips_mismatched_report_periods`。

### 2026-05-11 ~ 2026-05-10
- 已完成 A股可信度审计主链路接入（`report_audit` / `weighted_decision` / `cn_fact_snapshot`）并打通后端返回。
- 已完成角色数据准入门控、缺失字段结构化输出、目标价异常降级与 key_points 回填等核心机制。

---

## 测试记录（本轮）

- 命令：`venv\Scripts\python.exe -m pytest tests\test_cn_analysis_trust_audit.py -k "price_conflict or weighted_role_decision" -v`
- 结果：`5 passed, 1 failed`
  - 失败项：`test_cn_report_audit_detects_price_conflict`（本地缺少样本文件 `results/000002_分析报告_2026-05-11.json`，属于测试数据文件缺失，不是逻辑回归失败）
- 命令：`venv\Scripts\python.exe -m pytest tests\test_cn_financial_field_supplement.py -k "conflict_detection_skips_mismatched_report_periods or derive_total_liabilities or short_alias_pe" -v`
- 结果：`3 passed`

---

## 下一步从哪接着做

1. 用最新 `000002` 报告复跑审计，确认 `LOW_DATA_QUALITY` 是否只剩真实冲突（不再包含报告期错配冲突）。
2. 继续清理 `net_profit_yoy/roe` 这类疑似字段错配的来源映射（优先 `akshare_indicator_lg`）。
3. 追加一条回归：未知报告期来源不应压过已知同季度来源。

---

## 2026-05-12（本轮追加）

### 当前开发进度
- 已一次性完成“流程中断 + 审计误报”两条主线修复。
- 对 `results/000002_分析报告_2026-05-12.json` 复跑 `audit_cn_report`：当前返回 `issues=[]`。

### 最近改了什么
1. `tradingagents/graph/conditional_logic.py`
   - `should_continue_debate()` 对异常 `current_response` 增加兜底分支，返回 `Research Manager`，不再返回非法路由键。
2. `tradingagents/graph/setup.py`
   - 辩论路由映射补充自环键（`Bull Researcher` / `Bear Researcher`），避免图执行因未映射键触发 `KeyError`。
3. `tradingagents/graph/report_audit.py`
   - `LOW_DATA_QUALITY` 判定收敛：仅 `grade in {D,F}`、存在 `missing_required_fields`、或“有效冲突字段”时触发。
   - 新增冲突有效性过滤：百分比口径归一、金额尺度对齐、`net_profit_yoy/revenue_yoy` 离群值过滤、`eps` 单位尺度容错。
4. 新增/更新测试
   - 新增 `tests/test_graph_debate_routing.py`（辩论路由异常兜底与正常轮转）。
   - 更新 `tests/test_cn_analysis_trust_audit.py`（单位等价冲突、离群百分比冲突、EPS 单位冲突误报回归）。

### 下一步从哪接着做
1. 重新生成一次完整分析报告后继续全量收口。
2. 若新报告仍有异常，继续“集中修复所有剩余问题后再统一回报”。
# 2026-05-12（状态接口500修复补充）

## 当前开发进度
- 已修复“分析一半后状态查询报 500”的主因：状态数据缺少 `progress` 等字段导致接口异常。

## 最近改了什么
1. `app/services/simple_analysis_service.py`
   - `get_task_status()` 返回前统一补齐状态字段并规范 `progress`（数值化+0~100收敛）。
2. `app/routers/analysis.py`
   - `get_task_status_new()` 增加字段兜底，避免缺字段时抛出 500。

## 下一步从哪接着做
1. 继续处理最新报告里的剩余问题，集中修完再统一汇报。
2. 如再出现中途报错，按 task_id 回溯 `logs/tradingagents.log` 做整链路修复。
