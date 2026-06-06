#!/usr/bin/env python3
"""A股数据获取脚本 - 基于腾讯/新浪免费API + AKShare资金流向"""

import json
import sys
import subprocess
import time
import re
from datetime import datetime, timedelta

def ensure_dependencies():
    required = {"httpx": "httpx", "akshare": "akshare", "pandas": "pandas"}
    missing = []
    for module, package in required.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(package)
    if missing:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install"] + missing + ["-q"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

ensure_dependencies()

import httpx
import pandas as pd

# AKShare 仅用于资金流向（需要 monkey-patch）
import requests
_original_session_request = requests.Session.request
def _patched_session_request(self, method, url, **kwargs):
    try:
        return _original_session_request(self, method, url, **kwargs)
    except (requests.exceptions.ConnectionError, requests.exceptions.ChunkedEncodingError):
        if "eastmoney.com" in url:
            url = url.replace("https://", "http://")
        timeout = kwargs.pop("timeout", 30)
        if isinstance(timeout, tuple): timeout = timeout[1] if len(timeout) > 1 else timeout[0]
        params = kwargs.pop("params", None)
        headers = kwargs.pop("headers", None) or dict(self.headers)
        for k in ["verify", "stream", "cert", "proxies", "allow_redirects", "hooks", "data", "json"]: kwargs.pop(k, None)
        with httpx.Client(timeout=timeout, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"}) as client:
            resp = client.request(method, url, params=params, headers=headers)
        fake_resp = requests.Response()
        fake_resp.status_code = resp.status_code
        fake_resp._content = resp.content
        fake_resp.headers.update(resp.headers)
        fake_resp.encoding = resp.encoding or "utf-8"
        fake_resp.url = str(resp.url)
        return fake_resp
requests.Session.request = _patched_session_request
import akshare as ak


HEADERS = {"Referer": "https://finance.sina.com.cn", "User-Agent": "Mozilla/5.0"}
HTTP_CLIENT = httpx.Client(timeout=15, headers=HEADERS, follow_redirects=True)


def error_response(code, msg):
    return json.dumps({
        "code": code, "market": "A", "status": "error",
        "error": msg, "fallback_hint": "建议使用 WebSearch 获取近似数据"
    }, ensure_ascii=False, indent=2)


def _get_prefix(code):
    """A股代码前缀：6开头和5开头为沪市(sh)，其余为深市(sz)"""
    if code.startswith(("6", "5")):
        return "sh"
    return "sz"


# ============ 行情（腾讯 API）============

def _parse_tencent_quote(text):
    """解析腾讯行情数据"""
    match = re.search(r'"(.+)"', text)
    if not match:
        return None
    fields = match.group(1).split("~")
    if len(fields) < 50:
        return None
    return fields


def fetch_quote(code):
    """获取实时行情 - 腾讯 API"""
    try:
        prefix = _get_prefix(code)
        r = HTTP_CLIENT.get(f"http://qt.gtimg.cn/q={prefix}{code}")
        fields = _parse_tencent_quote(r.text)
        if not fields:
            return error_response(code, f"未找到股票代码 {code}")

        # 腾讯行情字段: [0]市场 [1]名称 [2]代码 [3]当前价 [4]昨收 [5]今开 [6]成交量(手)
        # [7]外盘 [8]内盘 [9]买1价 ... [30]最高 [31]最低 [32]价/涨跌/幅 [33]成交量(手)
        # [34]成交额(万) [35]换手率 [36]市盈率 [37]最高 [38]最低 [39]振幅 [40]流通市值
        # [41]总市值 [42]市净率 [43]涨停价 [44]跌停价 [45]量比
        price = float(fields[3]) if fields[3] else 0
        prev_close = float(fields[4]) if fields[4] else 0
        change_pct = round((price - prev_close) / prev_close * 100, 2) if prev_close else 0

        return json.dumps({
            "code": code, "name": fields[1], "market": "A",
            "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "data": {
                "price": price,
                "change_pct": change_pct,
                "volume": int(float(fields[6]) * 100) if fields[6] else 0,
                "amount": float(fields[37]) * 10000 if len(fields) > 37 and fields[37] else 0,
                "turnover_rate": float(fields[38]) if len(fields) > 38 and fields[38] else None,
                "high": float(fields[33]) if len(fields) > 33 and fields[33] else 0,
                "low": float(fields[34]) if len(fields) > 34 and fields[34] else 0,
                "open": float(fields[5]) if fields[5] else 0,
                "prev_close": prev_close,
                "pe": float(fields[39]) if len(fields) > 39 and fields[39] else None,
                "pb": float(fields[46]) if len(fields) > 46 and fields[46] else None,
                "volume_ratio": float(fields[49]) if len(fields) > 49 and fields[49] else None,
                "total_market_cap": float(fields[45]) if len(fields) > 45 and fields[45] else None,
                "circulating_market_cap": float(fields[44]) if len(fields) > 44 and fields[44] else None,
            },
            "status": "ok"
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return error_response(code, f"获取行情失败: {str(e)}")


# ============ 技术面（腾讯 K线 API）============

def fetch_technical(code):
    """获取技术面数据 - 腾讯日K线 API"""
    try:
        prefix = _get_prefix(code)
        url = f"https://proxy.finance.qq.com/ifzqgtimg/appstock/app/newfqkline/get?param={prefix}{code},day,,,250,qfq"
        r = HTTP_CLIENT.get(url)
        data = r.json()

        stock_key = f"{prefix}{code}"
        stock_data = data.get("data", {}).get(stock_key, {})
        kdata = stock_data.get("day") or stock_data.get("qfqday") or []

        if not kdata or len(kdata) < 60:
            return error_response(code, f"K线数据不足（仅{len(kdata)}条）")

        # 转为 DataFrame: [日期, 开, 收, 高, 低, 量, ...]
        df = pd.DataFrame(kdata, columns=["date", "open", "close", "high", "low", "volume"] + [f"x{i}" for i in range(len(kdata[0]) - 6)])
        close = df["close"].astype(float)
        high = df["high"].astype(float)
        low = df["low"].astype(float)
        volume = df["volume"].astype(float)

        # 均线
        ma5 = close.rolling(5).mean()
        ma10 = close.rolling(10).mean()
        ma20 = close.rolling(20).mean()
        ma60 = close.rolling(60).mean()

        lma5 = float(ma5.iloc[-1]) if not pd.isna(ma5.iloc[-1]) else None
        lma10 = float(ma10.iloc[-1]) if not pd.isna(ma10.iloc[-1]) else None
        lma20 = float(ma20.iloc[-1]) if not pd.isna(ma20.iloc[-1]) else None
        lma60 = float(ma60.iloc[-1]) if not pd.isna(ma60.iloc[-1]) else None

        if all(v is not None for v in [lma5, lma10, lma20, lma60]):
            if lma5 > lma10 > lma20 > lma60: ma_arrangement = "bullish"
            elif lma5 < lma10 < lma20 < lma60: ma_arrangement = "bearish"
            else: ma_arrangement = "tangled"
        else:
            ma_arrangement = "unknown"

        current_price = float(close.iloc[-1])
        deviation_60 = round((current_price - lma60) / lma60 * 100, 2) if lma60 else None
        momentum_20d = round((current_price / float(close.iloc[-20]) - 1) * 100, 2) if len(close) >= 20 else None
        momentum_60d = round((current_price / float(close.iloc[-60]) - 1) * 100, 2) if len(close) >= 60 else None

        # MACD
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        dif = ema12 - ema26
        dea = dif.ewm(span=9, adjust=False).mean()
        hist = 2 * (dif - dea)
        dif_val = round(float(dif.iloc[-1]), 3)
        dea_val = round(float(dea.iloc[-1]), 3)
        hist_val = round(float(hist.iloc[-1]), 3)
        if dif.iloc[-1] > dea.iloc[-1] and dif.iloc[-2] <= dea.iloc[-2]: macd_signal = "golden_cross"
        elif dif.iloc[-1] < dea.iloc[-1] and dif.iloc[-2] >= dea.iloc[-2]: macd_signal = "death_cross"
        elif dif.iloc[-1] > dea.iloc[-1]: macd_signal = "above"
        else: macd_signal = "below"

        # RSI
        def _rsi(series, period):
            delta = series.diff()
            gain = delta.where(delta > 0, 0).rolling(period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
            rs = gain / loss
            return 100 - (100 / (1 + rs))
        rsi6 = round(float(_rsi(close, 6).iloc[-1]), 2)
        rsi12 = round(float(_rsi(close, 12).iloc[-1]), 2)
        rsi24 = round(float(_rsi(close, 24).iloc[-1]), 2)

        # KDJ
        low9 = low.rolling(9).min()
        high9 = high.rolling(9).max()
        rsv = (close - low9) / (high9 - low9) * 100
        k = rsv.ewm(com=2, adjust=False).mean()
        d = k.ewm(com=2, adjust=False).mean()
        j = 3 * k - 2 * d
        k_val = round(float(k.iloc[-1]), 2)
        d_val = round(float(d.iloc[-1]), 2)
        j_val = round(float(j.iloc[-1]), 2)

        # 布林带
        boll_mid = close.rolling(20).mean()
        boll_std = close.rolling(20).std()
        boll_upper = boll_mid + 2 * boll_std
        boll_lower = boll_mid - 2 * boll_std
        bu = float(boll_upper.iloc[-1]) if not pd.isna(boll_upper.iloc[-1]) else None
        bm = float(boll_mid.iloc[-1]) if not pd.isna(boll_mid.iloc[-1]) else None
        bl = float(boll_lower.iloc[-1]) if not pd.isna(boll_lower.iloc[-1]) else None
        boll_pos = round((current_price - bl) / (bu - bl) * 100, 1) if bu and bl and (bu - bl) != 0 else None

        # ATR
        tr = pd.concat([high - low, abs(high - close.shift(1)), abs(low - close.shift(1))], axis=1).max(axis=1)
        atr14 = float(tr.rolling(14).mean().iloc[-1])
        atr_pct = round(atr14 / current_price * 100, 2)

        # 成交量
        vol5 = float(volume.iloc[-5:].mean())
        vol20 = float(volume.iloc[-20:].mean())
        vol_ratio = round(vol5 / vol20, 2) if vol20 > 0 else None
        volume_state = "heavy" if vol_ratio and vol_ratio > 1.5 else ("light" if vol_ratio and vol_ratio < 0.7 else "normal")

        high_52w = round(float(high.tail(min(252, len(high))).max()), 2)
        low_52w = round(float(low.tail(min(252, len(low))).min()), 2)

        return json.dumps({
            "code": code, "name": "", "market": "A",
            "timestamp": datetime.now().strftime("%Y-%m-%d"),
            "data": {
                "price": current_price,
                "ma": {"ma5": round(lma5, 2) if lma5 else None, "ma10": round(lma10, 2) if lma10 else None,
                       "ma20": round(lma20, 2) if lma20 else None, "ma60": round(lma60, 2) if lma60 else None},
                "ma_arrangement": ma_arrangement, "deviation_60": deviation_60,
                "momentum_20d": momentum_20d, "momentum_60d": momentum_60d,
                "macd": {"dif": dif_val, "dea": dea_val, "histogram": hist_val, "signal": macd_signal},
                "rsi": {"rsi6": rsi6, "rsi12": rsi12, "rsi24": rsi24},
                "kdj": {"k": k_val, "d": d_val, "j": j_val},
                "boll": {"upper": round(bu, 2) if bu else None, "mid": round(bm, 2) if bm else None,
                         "lower": round(bl, 2) if bl else None, "position_pct": boll_pos},
                "atr": {"atr14": round(atr14, 3), "atr_pct": atr_pct},
                "volume_state": volume_state, "volume_ratio_5_20": vol_ratio,
                "high_52w": high_52w, "low_52w": low_52w
            },
            "status": "ok"
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return error_response(code, f"获取技术面数据失败: {str(e)}")


# ============ 财务/估值（新浪 API）============

def _fetch_sina_extended(code):
    """获取新浪扩展行情数据（含 PE/PB/EPS/净利润等）"""
    prefix = _get_prefix(code)
    r = HTTP_CLIENT.get(f"http://hq.sinajs.cn/list={prefix}{code}_i")
    match = re.search(r'"(.+)"', r.text)
    if not match:
        return None
    return match.group(1).split(",")


def fetch_finance(code):
    """获取财务数据 - 新浪 API"""
    try:
        fields = _fetch_sina_extended(code)
        if not fields or len(fields) < 40:
            return error_response(code, "未获取到财务数据")

        # 字段解析
        eps = float(fields[2]) if fields[2] else None
        bps = float(fields[4]) if fields[4] else None  # 每股净资产（看实际意义）
        net_profit = float(fields[12]) * 1e8 if fields[12] else None  # 净利润(亿→元)
        roe = float(fields[16]) if fields[16] else None

        # field[39] 格式: "20250331|营收|净利润|..."
        revenue = None
        latest_report = None
        if len(fields) > 39 and fields[39]:
            parts = fields[39].split("|")
            if len(parts) >= 5:
                latest_report = parts[0]
                revenue = float(parts[1]) if parts[1] else None
                # parts[1]=营收, parts[2]=净利润, parts[3]=?, parts[4]=?

        # field[37] = 营收(元)
        if not revenue and len(fields) > 37 and fields[37]:
            try:
                revenue = float(fields[37])
            except:
                pass

        return json.dumps({
            "code": code, "name": fields[22] if len(fields) > 22 else "", "market": "A",
            "timestamp": datetime.now().strftime("%Y-%m-%d"),
            "data": {
                "eps": eps,
                "bps": bps,
                "net_profit": net_profit,
                "revenue": revenue,
                "roe": roe,
                "latest_report_date": latest_report,
            },
            "status": "ok"
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return error_response(code, f"获取财务数据失败: {str(e)}")


def fetch_valuation(code):
    """获取估值数据 - 腾讯 API（PE/PB/市值均从腾讯获取，数据准确）"""
    try:
        prefix = _get_prefix(code)
        r = HTTP_CLIENT.get(f"http://qt.gtimg.cn/q={prefix}{code}")
        tq_fields = _parse_tencent_quote(r.text)
        if not tq_fields:
            return error_response(code, "未获取到估值数据")

        pe_ttm = float(tq_fields[39]) if len(tq_fields) > 39 and tq_fields[39] else None
        pb = float(tq_fields[46]) if len(tq_fields) > 46 and tq_fields[46] else None
        total_mv = float(tq_fields[45]) if len(tq_fields) > 45 and tq_fields[45] else None
        circ_mv = float(tq_fields[44]) if len(tq_fields) > 44 and tq_fields[44] else None

        # 新浪补充 52 周高低和股息率
        sina_fields = _fetch_sina_extended(code)
        high_52w = None
        low_52w = None
        dividend_yield = None
        if sina_fields and len(sina_fields) > 24:
            try:
                parts = sina_fields[24].split("|")
                if len(parts) >= 2:
                    high_52w = float(parts[0]) if parts[0] else None
                    low_52w = float(parts[1]) if parts[1] else None
            except:
                pass
        if sina_fields and len(sina_fields) > 21:
            try:
                dividend_yield = float(sina_fields[21]) if sina_fields[21] else None
            except:
                pass

        return json.dumps({
            "code": code,
            "name": tq_fields[1] if len(tq_fields) > 1 else "",
            "market": "A",
            "timestamp": datetime.now().strftime("%Y-%m-%d"),
            "data": {
                "pe_ttm": pe_ttm,
                "pb": pb,
                "dividend_yield": dividend_yield,
                "total_market_cap": total_mv,
                "circulating_market_cap": circ_mv,
                "52w_high": high_52w,
                "52w_low": low_52w,
            },
            "status": "ok"
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return error_response(code, f"获取估值数据失败: {str(e)}")


# ============ 资金流向（AKShare）============

def fetch_fund_flow(code):
    """获取资金流向 - AKShare"""
    try:
        main_net_5d = None
        main_net_20d = None
        try:
            df_flow = ak.stock_individual_fund_flow(stock=code, market="sh" if code.startswith(("6",)) else "sz")
            if not df_flow.empty:
                main_net_5d = float(df_flow.head(5)["主力净流入-净额"].sum()) if "主力净流入-净额" in df_flow.columns else None
                main_net_20d = float(df_flow.head(20)["主力净流入-净额"].sum()) if "主力净流入-净额" in df_flow.columns else None
        except:
            pass

        north_today = None
        north_5d = None
        try:
            df_sh = ak.stock_hsgt_hist_em(symbol="沪股通")
            df_sz = ak.stock_hsgt_hist_em(symbol="深股通")
            col = "当日成交净买额"
            if not df_sh.empty and not df_sz.empty and col in df_sh.columns:
                north_today = (float(df_sh.iloc[-1][col]) if pd.notna(df_sh.iloc[-1][col]) else 0) + \
                              (float(df_sz.iloc[-1][col]) if pd.notna(df_sz.iloc[-1][col]) else 0)
                north_5d = float(df_sh.tail(5)[col].dropna().sum() + df_sz.tail(5)[col].dropna().sum())
        except:
            pass

        return json.dumps({
            "code": code, "name": "", "market": "A",
            "timestamp": datetime.now().strftime("%Y-%m-%d"),
            "data": {
                "main_net_inflow_5d": main_net_5d, "main_net_inflow_20d": main_net_20d,
                "north_net_flow_today": north_today, "north_net_flow_5d": north_5d,
                "margin_balance": None, "margin_balance_change_5d": None
            },
            "status": "ok"
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return error_response(code, f"获取资金流向失败: {str(e)}")


# ============ 全部 ============

def fetch_all(code):
    """获取全部数据"""
    results = {}
    results["quote"] = json.loads(fetch_quote(code))
    results["finance"] = json.loads(fetch_finance(code))
    results["technical"] = json.loads(fetch_technical(code))
    results["fund_flow"] = json.loads(fetch_fund_flow(code))
    results["valuation"] = json.loads(fetch_valuation(code))
    return json.dumps({
        "code": code, "market": "A",
        "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "modules": results, "status": "ok"
    }, ensure_ascii=False, indent=2)


def main():
    if len(sys.argv) < 3:
        print(json.dumps({"status": "error", "error": "用法: python3 fetch_a_stock.py <代码> <类型>",
                          "usage": "quote | finance | technical | fund_flow | valuation | all"}, ensure_ascii=False, indent=2))
        sys.exit(1)

    code = sys.argv[1].replace("SZ", "").replace("SH", "").replace("sz", "").replace("sh", "")
    data_type = sys.argv[2]
    dispatch = {"quote": fetch_quote, "finance": fetch_finance, "technical": fetch_technical,
                "fund_flow": fetch_fund_flow, "valuation": fetch_valuation, "all": fetch_all}

    if data_type not in dispatch:
        print(json.dumps({"status": "error", "error": f"不支持: {data_type}", "supported": list(dispatch.keys())}, ensure_ascii=False, indent=2))
        sys.exit(1)

    print(dispatch[data_type](code))

if __name__ == "__main__":
    main()
