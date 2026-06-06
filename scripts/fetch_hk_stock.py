#!/usr/bin/env python3
"""港股数据获取脚本 - 基于腾讯/新浪免费API"""

import json
import sys
import subprocess
import re
from datetime import datetime, timedelta

def ensure_dependencies():
    required = {"httpx": "httpx", "pandas": "pandas"}
    missing = []
    for module, package in required.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(package)
    if missing:
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing + ["-q"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

ensure_dependencies()

import httpx
import pandas as pd

HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://finance.sina.com.cn"}
HTTP_CLIENT = httpx.Client(timeout=15, headers=HEADERS, follow_redirects=True)


def error_response(code, msg):
    return json.dumps({"code": code, "market": "HK", "status": "error",
                       "error": msg, "fallback_hint": "建议使用 WebSearch 获取近似数据"}, ensure_ascii=False, indent=2)


def normalize_code(code):
    return code.replace(".HK", "").replace(".hk", "").zfill(5)


def fetch_quote(code):
    """获取港股实时行情 - 腾讯 API"""
    code = normalize_code(code)
    try:
        r = HTTP_CLIENT.get(f"http://qt.gtimg.cn/q=r_hk{code}")
        match = re.search(r'"(.+)"', r.text)
        if not match:
            return error_response(code, f"未找到港股代码 {code}")
        fields = match.group(1).split("~")
        if len(fields) < 30:
            return error_response(code, "数据格式异常")

        price = float(fields[3]) if fields[3] else 0
        prev_close = float(fields[4]) if fields[4] else 0
        change_pct = round((price - prev_close) / prev_close * 100, 2) if prev_close else 0

        return json.dumps({
            "code": code, "name": fields[1], "market": "HK",
            "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "data": {
                "price": price, "change_pct": change_pct,
                "volume": int(float(fields[6])) if fields[6] else 0,
                "high": float(fields[33]) if len(fields) > 33 and fields[33] else None,
                "low": float(fields[34]) if len(fields) > 34 and fields[34] else None,
                "open": float(fields[5]) if fields[5] else 0,
                "prev_close": prev_close,
                "pe": float(fields[39]) if len(fields) > 39 and fields[39] else None,
                "pb": float(fields[56]) if len(fields) > 56 and fields[56] else None,
                "total_market_cap": float(fields[45]) if len(fields) > 45 and fields[45] else None,
                "52w_high": float(fields[51]) if len(fields) > 51 and fields[51] else None,
                "52w_low": float(fields[52]) if len(fields) > 52 and fields[52] else None,
                "dividend_yield": float(fields[53]) if len(fields) > 53 and fields[53] else None,
            },
            "status": "ok"
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return error_response(code, f"获取行情失败: {str(e)}")


def fetch_technical(code):
    """获取港股技术面 - 腾讯K线"""
    code = normalize_code(code)
    try:
        url = f"https://proxy.finance.qq.com/ifzqgtimg/appstock/app/newfqkline/get?param=hk{code},day,,,250,qfq"
        r = HTTP_CLIENT.get(url)
        data = r.json()

        stock_key = f"hk{code}"
        stock_data = data.get("data", {}).get(stock_key, {})
        kdata = stock_data.get("day") or stock_data.get("qfqday") or []
        if not kdata or len(kdata) < 60:
            return error_response(code, f"K线数据不足（{len(kdata)}条）")

        df = pd.DataFrame(kdata, columns=["date", "open", "close", "high", "low", "volume"] + [f"x{i}" for i in range(max(0, len(kdata[0]) - 6))])
        close = df["close"].astype(float)
        high = df["high"].astype(float)
        low = df["low"].astype(float)
        volume = df["volume"].astype(float)

        # 计算指标（与A股逻辑相同）
        ma5 = close.rolling(5).mean()
        ma10 = close.rolling(10).mean()
        ma20 = close.rolling(20).mean()
        ma60 = close.rolling(60).mean()

        lma5, lma10, lma20, lma60 = [float(ma.iloc[-1]) if not pd.isna(ma.iloc[-1]) else None for ma in [ma5, ma10, ma20, ma60]]

        if all(v is not None for v in [lma5, lma10, lma20, lma60]):
            if lma5 > lma10 > lma20 > lma60: ma_arrangement = "bullish"
            elif lma5 < lma10 < lma20 < lma60: ma_arrangement = "bearish"
            else: ma_arrangement = "tangled"
        else:
            ma_arrangement = "unknown"

        cp = float(close.iloc[-1])
        dev60 = round((cp - lma60) / lma60 * 100, 2) if lma60 else None
        m20 = round((cp / float(close.iloc[-20]) - 1) * 100, 2) if len(close) >= 20 else None
        m60 = round((cp / float(close.iloc[-60]) - 1) * 100, 2) if len(close) >= 60 else None

        # MACD
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        dif = ema12 - ema26
        dea = dif.ewm(span=9, adjust=False).mean()
        dif_v, dea_v = round(float(dif.iloc[-1]), 3), round(float(dea.iloc[-1]), 3)
        hist_v = round(float(2*(dif.iloc[-1]-dea.iloc[-1])), 3)
        if dif.iloc[-1] > dea.iloc[-1] and dif.iloc[-2] <= dea.iloc[-2]: sig = "golden_cross"
        elif dif.iloc[-1] < dea.iloc[-1] and dif.iloc[-2] >= dea.iloc[-2]: sig = "death_cross"
        elif dif.iloc[-1] > dea.iloc[-1]: sig = "above"
        else: sig = "below"

        # RSI
        def _rsi(s, p):
            d = s.diff(); g = d.where(d>0,0).rolling(p).mean(); l = (-d.where(d<0,0)).rolling(p).mean()
            return round(float((100 - 100/(1+g/l)).iloc[-1]), 2)
        rsi6, rsi12, rsi24 = _rsi(close,6), _rsi(close,12), _rsi(close,24)

        # KDJ
        l9 = low.rolling(9).min(); h9 = high.rolling(9).max()
        rsv = (close - l9)/(h9 - l9)*100
        k = rsv.ewm(com=2, adjust=False).mean(); d = k.ewm(com=2, adjust=False).mean(); j = 3*k - 2*d

        # Boll
        bm = close.rolling(20).mean(); bs = close.rolling(20).std()
        bu = bm + 2*bs; bl = bm - 2*bs
        bu_v = float(bu.iloc[-1]) if not pd.isna(bu.iloc[-1]) else None
        bl_v = float(bl.iloc[-1]) if not pd.isna(bl.iloc[-1]) else None
        bm_v = float(bm.iloc[-1]) if not pd.isna(bm.iloc[-1]) else None
        bp = round((cp-bl_v)/(bu_v-bl_v)*100, 1) if bu_v and bl_v and (bu_v-bl_v)!=0 else None

        # ATR
        tr = pd.concat([high-low, abs(high-close.shift(1)), abs(low-close.shift(1))], axis=1).max(axis=1)
        atr14 = float(tr.rolling(14).mean().iloc[-1])

        # Volume
        v5 = float(volume.iloc[-5:].mean()); v20 = float(volume.iloc[-20:].mean())
        vr = round(v5/v20, 2) if v20 > 0 else None
        vs = "heavy" if vr and vr > 1.5 else ("light" if vr and vr < 0.7 else "normal")

        return json.dumps({
            "code": code, "name": "", "market": "HK", "timestamp": datetime.now().strftime("%Y-%m-%d"),
            "data": {
                "price": cp,
                "ma": {"ma5": round(lma5,2) if lma5 else None, "ma10": round(lma10,2) if lma10 else None,
                       "ma20": round(lma20,2) if lma20 else None, "ma60": round(lma60,2) if lma60 else None},
                "ma_arrangement": ma_arrangement, "deviation_60": dev60,
                "momentum_20d": m20, "momentum_60d": m60,
                "macd": {"dif": dif_v, "dea": dea_v, "histogram": hist_v, "signal": sig},
                "rsi": {"rsi6": rsi6, "rsi12": rsi12, "rsi24": rsi24},
                "kdj": {"k": round(float(k.iloc[-1]),2), "d": round(float(d.iloc[-1]),2), "j": round(float(j.iloc[-1]),2)},
                "boll": {"upper": round(bu_v,2) if bu_v else None, "mid": round(bm_v,2) if bm_v else None,
                         "lower": round(bl_v,2) if bl_v else None, "position_pct": bp},
                "atr": {"atr14": round(atr14,3), "atr_pct": round(atr14/cp*100, 2)},
                "volume_state": vs, "volume_ratio_5_20": vr,
                "high_52w": round(float(high.tail(252).max()),2), "low_52w": round(float(low.tail(252).min()),2)
            }, "status": "ok"
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return error_response(code, f"获取技术面数据失败: {str(e)}")


def fetch_finance(code):
    """获取港股财务数据 - 新浪"""
    code = normalize_code(code)
    try:
        r = HTTP_CLIENT.get(f"http://hq.sinajs.cn/list=rt_hk{code}")
        match = re.search(r'"(.+)"', r.text)
        if not match:
            return error_response(code, "未获取到数据")
        fields = match.group(1).split(",")
        # 新浪港股实时行情字段有限，财务数据主要从行情中提取
        name = fields[1] if len(fields) > 1 else ""
        pe = float(fields[7]) if len(fields) > 7 and fields[7] else None
        pb = float(fields[8]) if len(fields) > 8 and fields[8] else None
        dividend_yield = float(fields[9]) if len(fields) > 9 and fields[9] else None
        eps = float(fields[11]) if len(fields) > 11 and fields[11] else None

        return json.dumps({
            "code": code, "name": name, "market": "HK",
            "timestamp": datetime.now().strftime("%Y-%m-%d"),
            "data": {"eps": eps, "pe": pe, "pb": pb, "dividend_yield": dividend_yield,
                     "note": "港股详细财务数据建议通过 WebSearch 补充"},
            "status": "ok"
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return error_response(code, f"获取财务数据失败: {str(e)}")


def fetch_fund_flow(code):
    """港股资金流向（有限数据）"""
    code = normalize_code(code)
    return json.dumps({
        "code": code, "name": "", "market": "HK",
        "timestamp": datetime.now().strftime("%Y-%m-%d"),
        "data": {"south_net_flow_today": None, "south_net_flow_5d": None,
                 "note": "港股个股资金流向需通过 WebSearch 补充"},
        "status": "ok"
    }, ensure_ascii=False, indent=2)


def fetch_valuation(code):
    """获取港股估值 - 腾讯"""
    code = normalize_code(code)
    try:
        r = HTTP_CLIENT.get(f"http://qt.gtimg.cn/q=r_hk{code}")
        match = re.search(r'"(.+)"', r.text)
        if not match:
            return error_response(code, "未获取到数据")
        fields = match.group(1).split("~")

        return json.dumps({
            "code": code, "name": fields[1] if len(fields) > 1 else "", "market": "HK",
            "timestamp": datetime.now().strftime("%Y-%m-%d"),
            "data": {
                "pe_ttm": float(fields[39]) if len(fields) > 39 and fields[39] else None,
                "pb": float(fields[56]) if len(fields) > 56 and fields[56] else None,
                "total_market_cap": float(fields[45]) if len(fields) > 45 and fields[45] else None,
                "dividend_yield": float(fields[53]) if len(fields) > 53 and fields[53] else None,
                "52w_high": float(fields[51]) if len(fields) > 51 and fields[51] else None,
                "52w_low": float(fields[52]) if len(fields) > 52 and fields[52] else None,
            },
            "status": "ok"
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return error_response(code, f"获取估值数据失败: {str(e)}")


def fetch_all(code):
    results = {}
    results["quote"] = json.loads(fetch_quote(code))
    results["finance"] = json.loads(fetch_finance(code))
    results["technical"] = json.loads(fetch_technical(code))
    results["fund_flow"] = json.loads(fetch_fund_flow(code))
    results["valuation"] = json.loads(fetch_valuation(code))
    return json.dumps({"code": normalize_code(code), "market": "HK",
                       "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                       "modules": results, "status": "ok"}, ensure_ascii=False, indent=2)


def main():
    if len(sys.argv) < 3:
        print(json.dumps({"status": "error", "error": "用法: python3 fetch_hk_stock.py <代码> <类型>",
                          "example": "python3 fetch_hk_stock.py 00700 quote"}, ensure_ascii=False, indent=2))
        sys.exit(1)

    code = sys.argv[1]
    data_type = sys.argv[2]
    dispatch = {"quote": fetch_quote, "finance": fetch_finance, "technical": fetch_technical,
                "fund_flow": fetch_fund_flow, "valuation": fetch_valuation, "all": fetch_all}

    if data_type not in dispatch:
        print(json.dumps({"status": "error", "error": f"不支持: {data_type}"}, ensure_ascii=False, indent=2))
        sys.exit(1)
    print(dispatch[data_type](code))

if __name__ == "__main__":
    main()
