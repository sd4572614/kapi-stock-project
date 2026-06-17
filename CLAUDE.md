# A股市场分析项目

## 项目概述
本项目是一个A股市场分析系统，分为三个子项目：
1. **一级市场背景数据收集**（热点新闻、公司研报等）
2. **二级市场数据收集**（盘中资金流向、选股技术指标等）
3. **综合分析师**（整合一二级数据，产出分析结论）

## 子项目
| 子项目 | 路径 | 说明 |
|--------|------|------|
| A股投研看板 | `./投研看板` | 一级市场数据采集与投研看板前端 |

## 快速启动
```bash
# 方式1: 双击投研看板目录下的 start.bat
# 方式2: 手动启动
cd 投研看板 && D:\Python\python.exe a_stock_adapter.py   # 适配器自检
cd 投研看板\VIBE-TRADING\agent && D:\Python\python.exe run_server.py
```
启动后访问 http://127.0.0.1:8000/docs 查看 API 文档。

## 技术栈
- **Python 3.12** (D:\Python)
- **VIBE-TRADING** v0.1.9 (源码在 `./投研看板/VIBE-TRADING/`)
- **mootdx** 0.11.7 (通达信TCP直连)

## 目录结构
```
股票项目/
├── CLAUDE.md                 # 本文件
├── 投研看板/                 # A股投研看板子项目
│   ├── CLAUDE.md
│   ├── start.bat             # 一键启动
│   ├── a_stock_adapter.py    # A股数据适配器
│   ├── VIBE-TRADING/         # 投研交易平台
│   └── a-stock-data/         # A股数据源
└── (后续子项目...)
```
