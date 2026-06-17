---
name: industry-dashboard
version: 1.0.0
description: 行业产业链看板搭建技能 — 基于芯片/半导体/PCB板块搭建经验提炼，一键生成完整产业链分析看板（含总览、多环节子页、研报库、核心标的表、互动评分）
---

# 行业产业链看板搭建技能

## 功能概述

一键搭建完整的 A 股行业产业链分析看板，基于已成功交付的《芯片》《半导体》《PCB》三大板块经验提炼。

每个看板包含：
- **总览页**：产业链结构图、板块评分、核心标的池、成本构成、量产时间轴、板块结论
- **多环节子页**：环节定位、国际/国内竞争格局、科技/产能壁垒、核心标的表、个股评分体系
- **研报库**：东财行业研报（qType=1）、关键词筛选、分页浏览
- **互动功能**：点击个股切换专属评分、30秒自动刷新、localStorage自选持久化

## 调用方式

直接对我说以下任意一种即可触发：
- "搭建《XX》板块"
- "新建一个《XX》行业分析看板"
- "按照芯片板块的模式，创建《XX》板块"
- "/industry-dashboard XX"

我会自动完成：页面创建 → 路由注册 → 侧边栏导航 → 后端API扩展 → 构建部署。

## 搭建步骤（技能内部逻辑）

### Step 1: 确定板块结构

定义子分栏标签和关键词：

```
TABS = [
  总览, 研报库, 子环节A, 子环节B, 子环节C, ...
]
```

### Step 2: 创建页面文件（~500行）

基于模板创建 `frontend/src/pages/{Name}.tsx`，四个核心组件：

| 组件 | 说明 |
|------|------|
| `OverviewContent` | 产业链结构图 + 评分 + 标的池 + 成本构成 + 时间轴 + 结论 |
| `SegmentPage` | 每个子环节：定位/竞争格局/壁垒/标的表/评分 |
| `ReportsPage` | 研报列表 + 关键词筛选 + 分页 |
| `IndustryChain` | SVG/文字版产业链结构图 |

### Step 3: 填写产业数据

每个子环节需要填充 6 项产业级内容（~300字/项）：

- `positioning` — 环节在产业链中的位置、市场规模、增速
- `globalLandscape` — 全球格局：市场份额、主导企业、技术路线
- `chinaLandscape` — 国内格局：国产化率、龙头企业进展、差距
- `techBarrier` — 科技壁垒：技术难度、专利、认证周期
- `capacityBarrier` — 产能壁垒：资本开支、建设周期、供应链瓶颈
- `STOCKS[segment]` — 4-5 只核心 A 股标的（公司/不可替代性/评分/备注）

### Step 4: 个股评分数据

每只标的五维评分（1-5分）：

```typescript
INDIVIDUAL_SCORES: Record<string, Record<string, number>> = {
  "公司A": { irreplaceable: 5, valuation: 4, performance: 5, customer: 5, management: 4 },
  ...
}
```

板块综合评分（默认显示）：

```typescript
SCORES: Record<string, Record<string, number>> = {
  segmentA: { irreplaceable: 5, valuation: 3, performance: 4, customer: 4, management: 4 },
}
```

### Step 5: 研报库配置

配置关键词列表，复用 `/api/market/reports/chip` 端点：

```typescript
const REPORT_KEYWORDS = ["关键词A", "关键词B", "关键词C", ...]
```

### Step 6: 注册路由和导航

- `router.tsx`：添加 lazy import
- `Layout.tsx`：NAV 数组新增导航项

### Step 7: 构建验证

```bash
cd frontend && npm run build  # 零错误 → 重启服务器
```

## 数据源

| 数据 | 来源 | 说明 |
|------|------|------|
| 产业分析 | 行业知识库 | 环节定位、竞争格局、壁垒分析 |
| A股行情 | 腾讯财经 qt.gtimg.cn | 不封IP，实时现价/涨跌幅 |
| 美股行情 | yfinance | Yahoo Finance |
| 行业研报 | 东财 reportapi | qType=1，关键词搜索，最近3月 |
| A股搜索 | 腾讯 smartbox.gtimg.cn | 代码/名称模糊搜索 |

## 后端 API（已有的通用端点）

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/market/indices` | GET | 6大指数实时行情 |
| `/api/market/search/a?q=关键词` | GET | A股搜索 |
| `/api/market/quote/a` | POST | A股批量行情 |
| `/api/market/quote/us` | POST | 美股批量行情 |
| `/api/market/reports/chip` | GET | 行业研报（通用，传keyword参数） |

## 前端组件模板

### 产业链结构图

```
需求端 → 核心环节（5个虚线卡片） → 上游材料与设备
```

格式：顶部蓝色需求条 → 箭头 → 中间5个虚线边框卡片 → 箭头 → 底部6列上游网格。

### 板块评分总览

5环节星级评分 + 1-5级色条 + 一句话点评。

### 核心标的池

按环节分组展示公司名称，简洁列表格式。

### 成本构成

5项成本占比 + 每项说明文字。

### 量产时间轴

6个关键年份节点 + 事件描述，左边年份粗体。

### 板块结论

双列布局：绿色（确定性方向）+ 黄色（风险关注），项目符号列表。

## 已验证的板块

| 板块 | 分栏数 | 标的数 | 构建产物大小 |
|------|:--:|:--:|------|
| 芯片 | 7 | 24 | 36 KB |
| 半导体 | 7 | 25 | 41 KB |
| PCB | 6 | 18 | 37 KB |

## 注意事项

1. **中文引号问题**：产业数据中的中文引号 `""` 会导致 TypeScript 解析错误，必须替换为 `「」` 或直接去掉
2. **研报API跨关键词共用**：东财 API 不按关键词精准筛选，同一关键词返回全市场热门报告，研发库端点已内置去重
3. **个股数据不含代码**：目前核心标的表仅展示公司名称，不含股票代码，后续可接入行情API补充
4. **批量请求限流**：东财接口有频率限制，单次请求间隔 ≥0.3秒，批量拉取需控制并发
5. **页面懒加载**：React Router lazy() 模式，每个板块独立 chunk，不影响首页加载速度
