# -*- coding: utf-8 -*-
"""
A-Stock-Data 适配器 — 将 simonlin1212/a-stock-data 的核心数据获取能力
封装为可复用的 Python 模块，供 VIBE-TRADING 调用。

覆盖五层数据：行情✅、研报✅、新闻✅、基础数据✅、公告✅
数据源优先级：mootdx(通达信) > 腾讯财经 > 东财(限流) > 同花顺 > 新浪 > 巨潮

当前状态 (2026-06-17 实测):
  ✅ 行情层: 腾讯财经(PE/PB/市值/换手率) + mootdx(K线/盘口) — 不封IP
  ✅ 研报层: 东财 reportapi — 修复: code须纯数字+beginTime+endTime+qType
  ✅ 公告层: 巨潮 cninfo — 正常
  ✅ 新闻层: 同花顺快讯(全球) + 新浪(个股) — 正常
  ✅ 基础数据: 腾讯行情已覆盖 PE/PB/市值; 东财push2 不稳定降级
"""

import sys as _sys
for _s in ("stdout", "stderr"):
    _r = getattr(getattr(_sys, _s, None), "reconfigure", None)
    if callable(_r):
        _r(encoding="utf-8", errors="replace")

import time
import random
import requests
import pandas as pd
from functools import lru_cache

# ═══════════════════════════════════════════════════════════════════
# 基础设施
# ═══════════════════════════════════════════════════════════════════

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

# 东财限流
EM_SESSION = requests.Session()
EM_SESSION.headers.update({"User-Agent": UA})
EM_MIN_INTERVAL = 1.0
_em_last_call = [0.0]


def em_get(url: str, params: dict | None = None, headers: dict | None = None,
           timeout: int = 15, **kwargs):
    """东财统一请求入口：自动节流 + 复用 session"""
    wait = EM_MIN_INTERVAL - (time.time() - _em_last_call[0])
    if wait > 0:
        time.sleep(wait + random.uniform(0.1, 0.5))
    try:
        return EM_SESSION.get(url, params=params, headers=headers, timeout=timeout, **kwargs)
    finally:
        _em_last_call[0] = time.time()


def eastmoney_datacenter(report_name: str, columns: str = "ALL",
                          filter_str: str = "", page_size: int = 50,
                          sort_columns: str = "", sort_types: str = "-1") -> list[dict]:
    """东财数据中心统一查询"""
    params = {
        "reportName": report_name, "columns": columns,
        "filter": filter_str, "pageNumber": "1", "pageSize": str(page_size),
        "sortColumns": sort_columns, "sortTypes": sort_types,
        "source": "WEB", "client": "WEB",
    }
    r = em_get("https://datacenter-web.eastmoney.com/api/data/v1/get",
               params=params, timeout=15)
    d = r.json()
    if d.get("result") and d["result"].get("data"):
        return d["result"]["data"]
    return []


@lru_cache(maxsize=1)
def get_prefix(code: str) -> str:
    """6位代码 → 市场前缀"""
    code = str(code).zfill(6)
    if code.startswith(("6", "9")):
        return "sh"
    elif code.startswith("8"):
        return "bj"
    else:
        return "sz"


def normalize_code(code: str) -> str:
    """归一化为纯6位数字"""
    import re
    return re.sub(r"[^0-9]", "", str(code))[-6:].zfill(6)


# ═══════════════════════════════════════════════════════════════════
# 行情层 — mootdx (通达信) + 腾讯财经 (不封IP)
# ═══════════════════════════════════════════════════════════════════

def mootdx_kline(code: str, category: int = 4, offset: int = 30) -> pd.DataFrame:
    """
    mootdx K线数据
    category: 4=日线, 5=周线, 6=月线, 7=1分, 8=5分
    返回: open, close, high, low, vol, amount, datetime
    """
    from mootdx.quotes import Quotes
    client = Quotes.factory(market='std')
    code = normalize_code(code)
    data = client.bars(symbol=code, category=category, offset=offset)
    return pd.DataFrame(data) if data is not None else pd.DataFrame()


def mootdx_quote(codes: list[str]) -> pd.DataFrame:
    """mootdx 实时报价 (46字段: 现价/五档盘口/成交量等)"""
    from mootdx.quotes import Quotes
    client = Quotes.factory(market='std')
    codes = [normalize_code(c) for c in codes]
    data = client.quotes(symbol=codes)
    return pd.DataFrame(data) if data is not None else pd.DataFrame()


def tencent_quote(codes: list[str]) -> list[dict]:
    """
    腾讯财经 — PE/PB/市值/换手率/涨跌停价 (不封IP)
    返回每只股票的核心估值字段
    """
    import urllib.request

    code_map = {}
    for c in codes:
        c = normalize_code(c)
        prefix = get_prefix(c)
        code_map[f"{prefix}{c}"] = c

    url = f"http://qt.gtimg.cn/q={','.join(code_map.keys())}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    resp = urllib.request.urlopen(req, timeout=10)
    raw = resp.read().decode("gbk")

    results = []
    for line in raw.strip().split("\n"):
        if "~" not in line or '="' not in line:
            continue
        key = line.split("=")[0].replace("v_", "")
        values = line.split('"')[1].split("~")
        if len(values) < 50:
            continue
        original_code = code_map.get(key, key)
        results.append({
            "code": original_code,
            "name": values[1],
            "price": values[3],
            "last_close": values[4],
            "open": values[5],
            "high": values[33],
            "low": values[34],
            "volume": values[6],
            "amount": values[37],
            "change_pct": values[32],
            "pe_ttm": values[39],
            "pb": values[46],
            "market_cap": values[45],      # 总市值
            "circulating_cap": values[44], # 流通市值
            "turnover_rate": values[38],
            "high_limit": values[47],
            "low_limit": values[48],
        })
    return results


def tencent_index(codes: list[str]) -> list[dict]:
    """腾讯财经 — 指数/ETF行情"""
    import urllib.request
    results = []
    for batch in [codes[i:i+10] for i in range(0, len(codes), 10)]:
        url = f"http://qt.gtimg.cn/q={','.join(batch)}"
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        resp = urllib.request.urlopen(req, timeout=10)
        raw = resp.read().decode("gbk")
        for line in raw.strip().split("\n"):
            if "~" not in line:
                continue
            values = line.split('"')[1].split("~")
            if len(values) < 40:
                continue
            results.append({
                "code": line.split("=")[0].replace("v_", ""),
                "name": values[1],
                "price": values[3],
                "change_pct": values[32],
                "volume": values[6],
                "amount": values[37],
            })
    return results


# ═══════════════════════════════════════════════════════════════════
# 研报层 — 东财 reportapi + 同花顺一致预期
# ═══════════════════════════════════════════════════════════════════

def eastmoney_reports(code: str, page_size: int = 10, years: int = 1) -> list[dict]:
    """东财 — 个股研报列表 (含评级 + 三年EPS预测)

    Args:
        code: 股票代码 (6位纯数字)
        page_size: 返回条数
        years: 回溯年数 (默认1年)

    注意: 东财 reportapi 在 2026年变更, 关键修复:
    1. code 必须是纯6位数字 (不能带 sh/sz 前缀)
    2. 必须传 beginTime + endTime + qType
    """
    from datetime import datetime, timedelta
    code = normalize_code(code)
    end_time = datetime.now().strftime("%Y-%m-%d")
    begin_time = (datetime.now() - timedelta(days=365 * years)).strftime("%Y-%m-%d")
    params = {
        "code": code,  # 纯数字, 不带市场前缀!
        "pageSize": str(page_size),
        "pageNo": "1",
        "sort": "0",
        "beginTime": begin_time,
        "endTime": end_time,
        "qType": "0",
    }
    headers = {"User-Agent": UA, "Referer": "https://data.eastmoney.com/report/stock/"}
    r = requests.get("https://reportapi.eastmoney.com/report/list",
                     params=params, headers=headers, timeout=15)
    if r.status_code == 200:
        data = r.json()
        if data.get("data"):
            return data["data"]
    return []


def tonghuashun_consensus_eps(code: str) -> dict | None:
    """同花顺 — 机构一致预期EPS (直连 basic.10jqka.com.cn)"""
    code = normalize_code(code)
    url = f"https://basic.10jqka.com.cn/api/stockph/forecast/{code}/"
    headers = {
        "User-Agent": UA,
        "Referer": "https://basic.10jqka.com.cn/",
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            j = r.json()
            if j.get("data"):
                return j["data"]
    except Exception:
        pass
    return None


# ═══════════════════════════════════════════════════════════════════
# 新闻层 — 东财个股新闻 + 全球资讯
# ═══════════════════════════════════════════════════════════════════

def eastmoney_stock_news(code: str, page_size: int = 10) -> list[dict]:
    """个股新闻 — 新浪财经 (search-api-web 已改为用户搜索, 改用新浪)"""
    code = normalize_code(code)
    results = []

    # 端点1: 新浪财经个股新闻
    try:
        url = f"https://vip.stock.finance.sina.com.cn/corp/go.php/vCB_AllNewsStock/symbol/{get_prefix(code)}{code}.phtml"
        r = requests.get(url, headers={"User-Agent": UA, "Referer": "https://finance.sina.com.cn/"}, timeout=15)
        if r.status_code == 200:
            # 简单提取新闻标题（新浪返回HTML）
            from html.parser import HTMLParser

            class NewsParser(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.news = []
                    self.in_item = False
                    self.current = {}
                    self.data_key = None

                def handle_starttag(self, tag, attrs):
                    attrs_dict = dict(attrs)
                    if tag == "a" and "target" in attrs_dict:
                        self.current = {"url": attrs_dict.get("href", "")}
                        self.data_key = "title"
                    elif tag == "span":
                        self.data_key = "date"

                def handle_data(self, data):
                    if self.data_key and self.current is not None:
                        self.current[self.data_key] = data.strip()
                        self.data_key = None
                        if "title" in self.current and "date" in self.current:
                            if len(self.current.get("title", "")) > 5:
                                self.news.append(dict(self.current))
                            self.current = {}

            try:
                parser = NewsParser()
                parser.feed(r.text)
                results = parser.news[:page_size]
            except Exception:
                pass
    except Exception:
        pass

    # 端点2: 东财 search-api (降级, 可能只返回用户)
    if not results:
        try:
            params = {"keyword": code, "pageSize": str(page_size), "pageIndex": "1"}
            headers = {"User-Agent": UA, "Referer": "https://so.eastmoney.com/"}
            r = requests.get("https://search-api-web.eastmoney.com/search/jsonp",
                           params=params, headers=headers, timeout=15)
            if r.status_code == 200:
                text = r.text
                if text.startswith("jQuery"):
                    text = text[text.find("(")+1:text.rfind(")")]
                j = __import__('json').loads(text)
                for key in ["cmsArticleWebOld", "cmsArticleWeb"]:
                    articles = j.get("result", {}).get(key, [])
                    if isinstance(articles, list):
                        for a in articles:
                            results.append({"title": a.get("title", ""), "url": a.get("url", ""),
                                          "date": a.get("date", ""), "source": a.get("mediaName", "")})
        except Exception:
            pass

    return results[:page_size]


def eastmoney_global_news() -> list[dict]:
    """全球财经资讯 — 东财 np-weblist (已下线404) + 同花顺快讯降级"""
    results = []

    # 端点1: 东财新版快讯接口
    try:
        params = {"page": "1", "size": "20"}
        headers = {"User-Agent": UA, "Referer": "https://www.eastmoney.com/"}
        r = requests.get("https://np-listapi.eastmoney.com/comm/web/getNewsListByJson",
                        params=params, headers=headers, timeout=15)
        if r.status_code == 200:
            data = r.json()
            articles = data.get("data", {}).get("list", [])
            for a in articles:
                results.append({"title": a.get("title"), "url": a.get("url"),
                               "source": a.get("source", "东财"), "time": a.get("showTime")})
    except Exception:
        pass

    # 端点2: 同花顺快讯 (降级)
    if not results:
        try:
            headers = {"User-Agent": UA, "Referer": "https://www.10jqka.com.cn/"}
            r = requests.get("https://news.10jqka.com.cn/tapp/news/push/stock/",
                           params={"page": "1", "tag": ""}, headers=headers, timeout=15)
            if r.status_code == 200:
                data = r.json()
                items = data.get("data", {}).get("list", [])
                for it in items:
                    results.append({"title": it.get("title"), "url": it.get("url"),
                                   "source": "同花顺", "time": it.get("ctime")})
        except Exception:
            pass

    return results[:20]


# ═══════════════════════════════════════════════════════════════════
# 基础数据层 — mootdx 财务 + 东财个股信息 + 新浪三表
# ═══════════════════════════════════════════════════════════════════

def mootdx_finance(code: str) -> dict:
    """mootdx — 季报快照 (37字段: EPS/ROE/净利润/主营收入等)"""
    from mootdx.quotes import Quotes
    client = Quotes.factory(market='std')
    code = normalize_code(code)
    data = client.finance(symbol=code)
    if data is not None and len(data) > 0:
        latest = data.iloc[-1] if hasattr(data, 'iloc') else data[-1]
        return dict(latest) if hasattr(latest, 'items') else latest
    return {}


def mootdx_f10(code: str, category: str = "gszl") -> str:
    """mootdx — F10 公司资料 (9大类)
    category: gszl/gsjj/zyfz/jyfx/cwfx/gdjj/jjjj/ylgg/gszl_detail
    """
    from mootdx.quotes import Quotes
    client = Quotes.factory(market='std')
    code = normalize_code(code)
    try:
        result = client.f10(symbol=code, category=category)
        return str(result) if result else ""
    except Exception:
        return ""


def eastmoney_stock_info(code: str) -> dict:
    """东财 — 个股基本信息 (行业/总股本/流通股/市值/上市日期)"""
    code = normalize_code(code)
    params = {
        "fields": "f57,f58,f20,f21,f9,f115,f116,f117,f162,f167",
        "secids": f"1.{get_prefix(code)}{code}",
    }
    headers = {"User-Agent": UA, "Referer": "https://quote.eastmoney.com/"}
    r = em_get("https://push2.eastmoney.com/api/qt/stock/get",
               params=params, headers=headers, timeout=15)
    try:
        d = r.json().get("data", {})
        return {
            "code": code, "name": d.get("f58"), "market_cap": d.get("f20"),
            "circulating_cap": d.get("f21"), "pe_ttm": d.get("f115"),
            "pb": d.get("f167"), "industry": d.get("f162"),
            "total_shares": d.get("f57"), "list_date": d.get("f117"),
        }
    except Exception:
        return {}


def sina_financial_reports(code: str) -> dict:
    """新浪 — 财报三表 (资产负债表/利润表/现金流量表)"""
    code = normalize_code(code)
    prefix = get_prefix(code)
    results = {"balance_sheet": None, "income_statement": None, "cash_flow": None}
    tables = {"balance_sheet": "bs", "income_statement": "is", "cash_flow": "cf"}

    for name, table_key in tables.items():
        url = f"https://quotes.sina.cn/cn/api/jsonp_v2.php/data/Stock_{table_key}Service.getReportList?code={prefix}{code}"
        headers = {"User-Agent": UA, "Referer": "https://quotes.sina.cn/"}
        try:
            r = requests.get(url, headers=headers, timeout=10)
            text = r.text
            if text.startswith("jsonp"):
                text = text[text.find("(")+1:text.rfind(")")]
            j = __import__('json').loads(text)
            report_data = j.get("result", {}).get("data", {})

            # 取最新一个报告期
            report_list = report_data.get("report_list", {})
            if report_list:
                latest_period = list(report_list.keys())[0]
                items = report_list[latest_period].get("data", [])
                results[name] = {it.get("item_title"): it.get("item_value")
                                 for it in items}
        except Exception:
            pass
    return results


# ═══════════════════════════════════════════════════════════════════
# 公告层 — 巨潮 cninfo
# ═══════════════════════════════════════════════════════════════════

@lru_cache(maxsize=1)
def _cninfo_org_id_map() -> dict:
    """加载巨潮 orgId 映射表（模块级缓存）"""
    import json, os
    local = os.path.join(os.path.dirname(__file__), "szse_stock.json")
    if os.path.exists(local):
        with open(local, "r") as f:
            return json.load(f) or {}
    # 尝试从远程加载
    url = "https://www.cninfo.com.cn/data20/stock/data/szse_stock.json"
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=15)
        if r.status_code == 200:
            data = r.json()
            # 缓存到本地
            with open(local, "w") as f:
                json.dump(data, f)
            return data or {}
    except Exception:
        pass
    return {}


def cninfo_announcements(code: str, page_size: int = 10) -> list[dict]:
    """巨潮 — 公告全文检索"""
    code = normalize_code(code)
    prefix = get_prefix(code)
    # 巨潮 orgId 格式: gssz0{code} (深/北) / gssh0{code} (沪)
    org_id = f"gssz0{code}" if prefix in ("sz", "bj") else f"gssh0{code}"
    # 尝试从映射表查找
    try:
        org_map = _cninfo_org_id_map()
        if code in org_map:
            org_id = org_map[code]
    except Exception:
        pass

    params = {
        "stock": f"{code},{org_id}",
        "pageSize": str(page_size), "pageNum": "1",
        "column": "szse", "tabName": "fulltext",
        "sortName": "declaredDate", "sortType": "desc",
    }
    headers = {"User-Agent": UA, "Referer": "http://www.cninfo.com.cn/"}
    try:
        r = requests.post(
            "https://www.cninfo.com.cn/new/hisAnnouncement/query",
            data=params, headers=headers, timeout=15
        )
        if r.status_code == 200:
            data = r.json()
            anns = data.get("announcements", [])
            return [{"title": a.get("announcementTitle"),
                     "date": a.get("declaredDate"),
                     "url": f"https://www.cninfo.com.cn/new/disclosure/detail?annId={a.get('announcementId')}",
                     "type": a.get("announcementTypeName")}
                    for a in anns]
    except Exception:
        pass

    # 降级: 尝试旧版 endpoint
    try:
        r = requests.post(
            "https://www.cninfo.com.cn/new/fulltextSearch/full",
            data=params, headers=headers, timeout=15
        )
        if r.status_code == 200:
            data = r.json()
            anns = data.get("announcements", [])
            return [{"title": a.get("announcementTitle"),
                     "date": a.get("declaredDate"),
                     "url": f"https://www.cninfo.com.cn/new/disclosure/detail?annId={a.get('announcementId')}",
                     "type": a.get("announcementTypeName")}
                    for a in anns]
    except Exception:
        return []
    return []


# ═══════════════════════════════════════════════════════════════════
# 综合查询 — 一键获取标的全部关键信息
# ═══════════════════════════════════════════════════════════════════

def get_stock_overview(code: str) -> dict:
    """
    一键获取标的全景数据：行情 + 估值 + 新闻 + 研报 + 公告
    这是 VIBE-TRADING 的主要调用入口
    """
    code = normalize_code(code)
    result = {"code": code, "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")}

    # 行情 (腾讯 — 不封IP)
    try:
        quotes = tencent_quote([code])
        result["quote"] = quotes[0] if quotes else {}
    except Exception as e:
        result["quote"] = {"error": str(e)}

    # 基础信息
    try:
        result["info"] = eastmoney_stock_info(code)
    except Exception as e:
        result["info"] = {"error": str(e)}

    # 新闻
    try:
        result["news"] = eastmoney_stock_news(code, page_size=5)
    except Exception as e:
        result["news"] = {"error": str(e)}

    # 研报
    try:
        result["reports"] = eastmoney_reports(code, page_size=5)
    except Exception as e:
        result["reports"] = {"error": str(e)}

    # 公告
    try:
        result["announcements"] = cninfo_announcements(code, page_size=5)
    except Exception as e:
        result["announcements"] = {"error": str(e)}

    return result


# ═══════════════════════════════════════════════════════════════════
# 自检函数
# ═══════════════════════════════════════════════════════════════════

def self_test() -> dict:
    """运行自检，确认各层数据源能正常取数"""
    results = {}
    test_code = "600519"  # 贵州茅台 — 数据最全的测试标的

    print(f"🔍 A-Stock-Data 适配器自检 (测试标的: {test_code} 贵州茅台)\n")

    # 1. 行情层
    print("📊 行情层测试...")
    try:
        quote = tencent_quote([test_code])
        results["行情-腾讯"] = "✅" if quote and quote[0].get("name") else "⚠️ 返回异常"
        print(f"  腾讯财经: {results['行情-腾讯']} — {quote[0].get('name', '?')} PE={quote[0].get('pe_ttm', '?')}")
    except Exception as e:
        results["行情-腾讯"] = f"❌ {e}"
        print(f"  腾讯财经: ❌ {e}")

    try:
        kline = mootdx_kline(test_code, category=4, offset=5)
        results["行情-mootdx"] = "✅" if len(kline) > 0 else "⚠️ 返回空"
        print(f"  mootdx K线: {results['行情-mootdx']} — {len(kline)} 条")
    except Exception as e:
        results["行情-mootdx"] = f"❌ {e}"
        print(f"  mootdx K线: ❌ {e}")

    # 2. 研报层
    print("\n📝 研报层测试...")
    try:
        reports = eastmoney_reports(test_code, page_size=3)
        results["研报-东财"] = "✅" if reports else "⚠️ 返回空(可能无新研报)"
        print(f"  东财研报: {results['研报-东财']} — {len(reports) if isinstance(reports, list) else 0} 篇")
    except Exception as e:
        results["研报-东财"] = f"❌ {e}"
        print(f"  东财研报: ❌ {e}")

    # 3. 新闻层
    print("\n📰 新闻层测试...")
    try:
        news = eastmoney_stock_news(test_code, page_size=5)
        results["新闻-个股"] = "✅" if news else "⚠️ 返回空"
        print(f"  个股新闻: {results['新闻-个股']} — {len(news) if isinstance(news, list) else 0} 条")
    except Exception as e:
        results["新闻-个股"] = f"❌ {e}"
        print(f"  个股新闻: ❌ {e}")

    try:
        global_news = eastmoney_global_news()
        results["新闻-全球"] = "✅" if global_news else "⚠️ 返回空"
        print(f"  全球资讯: {results['新闻-全球']} — {len(global_news) if isinstance(global_news, list) else 0} 条")
    except Exception as e:
        results["新闻-全球"] = f"❌ {e}"
        print(f"  全球资讯: ❌ {e}")

    # 4. 基础数据层
    print("\n📋 基础数据层测试...")
    try:
        info = eastmoney_stock_info(test_code)
        results["基础-东财信息"] = "✅" if info.get("name") else "⚠️ 返回异常"
        print(f"  东财信息: {results['基础-东财信息']} — {info.get('name', '?')} 行业={info.get('industry', '?')}")
    except Exception as e:
        results["基础-东财信息"] = f"❌ {e}"
        print(f"  东财信息: ❌ {e}")

    # 5. 公告层
    print("\n📢 公告层测试...")
    try:
        anns = cninfo_announcements(test_code, page_size=5)
        results["公告-巨潮"] = "✅" if anns else "⚠️ 返回空"
        print(f"  巨潮公告: {results['公告-巨潮']} — {len(anns) if isinstance(anns, list) else 0} 条")
    except Exception as e:
        results["公告-巨潮"] = f"❌ {e}"
        print(f"  巨潮公告: ❌ {e}")

    # 打印总结
    print("\n" + "=" * 50)
    ok = sum(1 for v in results.values() if v.startswith("✅") or v.startswith("⚠️"))
    total = len(results)
    print(f"自检完成: {ok}/{total} 项可用")

    return results


if __name__ == "__main__":
    self_test()
