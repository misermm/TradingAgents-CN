<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-07 | Updated: 2026-05-07 -->

# utils

## Purpose
工具函数层，提供认证处理、日期时间格式化、市场类型判断、股票代码兼容性转换和格式验证等通用功能。

## Key Files

| File | Description |
|------|-------------|
| `auth.ts` | 认证工具：错误检测/处理、Token 有效性验证/解析/过期检查、自动刷新定时器 |
| `datetime.ts` | 日期时间工具：格式化（含时区处理）、相对时间、日期/时间分离显示，统一 UTC+8 输出 |
| `market.ts` | 市场判断工具：板块/交易所/代码 → A股/美股/港股 规范化映射 |
| `stock.ts` | 股票代码工具：字段兼容性（symbol/stock_code/code）、代码验证/格式化/市场推断/批量标准化 |
| `stockValidator.ts` | 股票代码验证器：A股/美股/港股格式校验、自动识别市场、格式说明和示例 |

## For AI Agents

### Working In This Directory
- 时区处理：后端入库为 UTC+8 但可能无时区标志，`formatDateTime` 自动补 `+08:00` 后缀
- 股票代码兼容：`getStockSymbol(obj)` 统一获取代码，`normalizeStockObject/Array` 批量补全兼容字段
- 市场判断优先级：`marketHint` 参数 > 代码格式自动识别（6位数字→A股，1-5位数字→港股，字母→美股）
- Token 刷新策略：`setupTokenRefreshTimer()` 每分钟检查，过期前 5 分钟自动刷新

### Testing Requirements
- 时区边界测试：验证无时区字符串、带 Z 后缀、带 +08:00 后缀的处理
- 股票代码验证：覆盖 A股前缀（60/68/00/30/43/83/87）、美股字母、港股数字
- 市场识别：验证 `normalizeMarketForAnalysis` 的所有映射路径

### Common Patterns
- 时间格式化：`formatDateTime(str)` → 自动补时区 → `toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })`
- 相对时间：`formatRelativeTime(str)` → 计算时间差 → "X天前/X小时前/刚刚"
- 股票代码标准化：`validateStockCode(code, marketHint?)` → `StockValidationResult { valid, market, normalizedCode }`
- 市场推断：`inferMarketCode('000001')` → `'SZ'`，`buildFullSymbol('000001')` → `'000001.SZ'`

## Dependencies

### Internal
- `@/stores/auth` - 认证状态（Token 刷新）
- `@/router` - 路由跳转（认证错误处理）

### External
- Element Plus - `ElMessage` 错误提示

<!-- MANUAL: Custom project notes can be added below -->
