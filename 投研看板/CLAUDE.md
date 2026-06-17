# A股投研看板

## 项目定位
本子项目是 [A股市场分析项目](../CLAUDE.md) 的一部分，负责：
- **一级市场背景数据收集**：热点新闻、公司研报等信息的采集与展示
- **投研看板前端**：将采集到的信息以看板形式呈现，支撑投资决策

## 快速启动
双击 `start.bat` 一键启动，或手动运行：
```bash
# 1. 数据适配器自检
D:\Python\python.exe a_stock_adapter.py

# 2. VIBE-TRADING API 服务器
cd VIBE-TRADING\agent && D:\Python\python.exe -m uvicorn api_server:app --host 127.0.0.1 --port 8000
```
服务地址: http://127.0.0.1:8000 | API 文档: http://127.0.0.1:8000/docs

## 技术栈
- **Python 3.12** (D:\Python)
- **VIBE-TRADING** v0.1.9 (源码在 `./VIBE-TRADING/`，pip editable install)
- **A-Stock-Data** (simonlin1212/a-stock-data) — 源码在 `./a-stock-data/`

## 目录结构
```
投研看板/
├── CLAUDE.md              # 本文件
├── start.bat              # 一键启动脚本
├── a_stock_adapter.py     # A股数据适配器 (行情/研报/新闻/公告/基础数据)
├── VIBE-TRADING/          # 投研交易平台 (pip editable)
│   └── agent/
│       ├── api_server.py  # FastAPI 服务端
│       ├── src/           # 核心逻辑
│       └── backtest/      # 回测引擎
└── a-stock-data/          # A股数据源脚本集
```

## A-Stock-Data 数据源状态

| 数据层 | 数据源 | 状态 | 覆盖内容 |
|--------|--------|:--:|------|
| 行情 | 腾讯财经 | ✅ | 现价/PE/PB/市值/换手率/涨跌停 |
| 行情 | mootdx (通达信) | ✅ | K线/五档盘口/逐笔成交 |
| 新闻 | 同花顺快讯 | ✅ | 全球财经资讯 |
| 公告 | 巨潮 cninfo | ✅ | 沪深北全量公告 |
| 基础数据 | 腾讯行情 | ✅ | PE/PB/市值已含 |
| 研报 | 东财 reportapi | ✅ | 个股研报 + EPS预测 |
| 基础信息 | 东财 push2 | ⚠️ | 连接不稳定 |

## 关键文件
- `a_stock_adapter.py` — A股数据适配器，封装五层数据源调用
- `VIBE-TRADING/agent/api_server.py` — VIBE-TRADING FastAPI 服务端

## 依赖关系
- 父项目：`D:\ai\股票项目`
- 依赖：VIBE-TRADING (pip editable install from `./VIBE-TRADING/`)
- 相关子项目：二级市场数据采集、综合分析师（尚未创建）
