# A股投研看板

## 项目定位
本子项目是 [A股市场分析项目](../CLAUDE.md) 的一部分，负责：
- **一级市场背景数据收集**：热点新闻、公司研报等信息的采集与展示
- **投研看板前端**：将采集到的信息以看板形式呈现，支撑投资决策

## 技术栈
- **Python 3.12** (D:\Python)
- **VIBE-TRADING** v0.1.9 (投研交易平台)
- **A-Stock-Data** (simonlin1212/a-stock-data) — A股数据采集

## A-Stock-Data 数据源状态

| 数据层 | 数据源 | 状态 | 覆盖内容 |
|--------|--------|:--:|------|
| 行情 | 腾讯财经 | ✅ | 现价/PE/PB/市值/换手率/涨跌停 |
| 行情 | mootdx (通达信) | ✅ | K线/五档盘口/逐笔成交 |
| 新闻 | 同花顺快讯 | ✅ | 全球财经资讯 |
| 公告 | 巨潮 cninfo | ✅ | 沪深北全量公告 |
| 基础数据 | 腾讯行情 | ✅ | PE/PB/市值已含 |
| 研报 | 东财 reportapi | ⚠️ | API参数变更,待修复 |
| 基础信息 | 东财 push2 | ⚠️ | 连接不稳定 |

## 关键文件
- `a_stock_adapter.py` — A股数据适配器，封装各数据源调用
- `D:\Python\Lib\site-packages\api_server.py` — VIBE-TRADING 服务端

## 依赖关系
- 父项目：`D:\ai\股票项目`
- 依赖：VIBE-TRADING (pip), a-stock-data (SKILL.md)
- 相关子项目：二级市场数据采集、综合分析师（尚未创建）
