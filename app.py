import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import warnings, io, json, time, requests, math
warnings.filterwarnings('ignore')

st.set_page_config(page_title="محلل الأسهم الذكي Pro v3",page_icon="📈",layout="wide",initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap');
*{box-sizing:border-box;}
html,body,[class*="css"]{font-family:'Cairo',sans-serif;background:#0d1117;color:#e6edf3;}
.stApp{background:#0d1117;}
.block-container{padding:1rem 1.5rem 3rem;}
.pro-header{background:linear-gradient(135deg,#0d1117,#161b22);border-bottom:1px solid #30363d;padding:1.4rem;text-align:center;border-radius:0 0 16px 16px;margin-bottom:1.2rem;}
.pro-header h1{font-size:1.9rem;font-weight:900;background:linear-gradient(90deg,#58a6ff,#bc8cff,#3fb950);-webkit-background-clip:text;-webkit-text-fill-color:transparent;}
.pro-header p{color:#8b949e;font-size:.85rem;margin-top:.2rem;}
.card{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:1.1rem;margin-bottom:.7rem;}
.card:hover{border-color:#58a6ff;}
.verdict-box{border-radius:14px;padding:1.4rem;text-align:center;border:2px solid;margin:.8rem 0;}
.v-strong-buy{background:rgba(63,185,80,.12);border-color:#3fb950;}
.v-buy{background:rgba(88,166,255,.10);border-color:#58a6ff;}
.v-hold{background:rgba(210,153,34,.10);border-color:#d29922;}
.v-reduce{background:rgba(240,136,62,.10);border-color:#f0883e;}
.v-sell{background:rgba(248,81,73,.14);border-color:#f85149;}
.verdict-title{font-size:2rem;font-weight:900;}
.verdict-sub{color:#8b949e;font-size:.88rem;margin-top:.3rem;}
.badge{display:inline-block;padding:.2rem .65rem;border-radius:20px;font-size:.74rem;font-weight:700;}
.b-green{background:rgba(63,185,80,.2);color:#3fb950;}
.b-red{background:rgba(248,81,73,.2);color:#f85149;}
.b-yellow{background:rgba(210,153,34,.2);color:#d29922;}
.b-blue{background:rgba(88,166,255,.2);color:#58a6ff;}
.b-purple{background:rgba(188,140,255,.2);color:#bc8cff;}
.b-orange{background:rgba(240,136,62,.2);color:#f0883e;}
.metric-card{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:.9rem;text-align:center;}
.metric-val{font-size:1.45rem;font-weight:900;}
.metric-lbl{color:#8b949e;font-size:.75rem;margin-top:.15rem;}
.news-item{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:.85rem;margin-bottom:.5rem;}
.stTabs [data-baseweb="tab"]{font-family:'Cairo',sans-serif;font-size:.88rem;}
.stButton>button{border-radius:10px;font-family:'Cairo',sans-serif;font-weight:700;}
.ai-box{background:linear-gradient(135deg,#161b22,#0d1117);border:1px solid #58a6ff;border-radius:12px;padding:1.2rem;margin:.8rem 0;}
.portfolio-card{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:1rem;margin-bottom:.6rem;}
.alert-card{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:.9rem;margin-bottom:.5rem;}
.summary-bar{background:linear-gradient(135deg,#161b22,#0d1420);border:1px solid #30363d;border-radius:10px;padding:.8rem 1.2rem;margin-bottom:.8rem;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:.5rem;}
.signal-row{display:flex;justify-content:space-between;padding:.5rem 0;border-bottom:1px solid #21262d;}
.signal-row:last-child{border-bottom:none;}
.target-row{display:flex;justify-content:space-between;align-items:center;padding:.6rem .9rem;border-radius:8px;margin-bottom:.4rem;}
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════
# مصادر البيانات
# ═══════════════════════════════════════════════════════

def to_stooq_symbol(symbol: str, market: str) -> str:
    s = symbol.upper().strip()
    mapping = {"sa":"sr","saudi":"sr","tasi":"sr","us":"us","ae":"ae","gb":"uk","de":"de"}
    suffix = mapping.get(market, "us")
    return f"{s.lower()}.{suffix}"

def fetch_stooq(symbol: str, market: str) -> pd.DataFrame:
    stooq_sym = to_stooq_symbol(symbol, market)
    url = f"https://stooq.com/q/d/l/?s={stooq_sym}&i=d"
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200 or "No data" in r.text or len(r.text) < 50:
            return pd.DataFrame()
        from io import StringIO
        df = pd.read_csv(StringIO(r.text))
        df.columns = [c.strip().lower() for c in df.columns]
        if 'date' not in df.columns: return pd.DataFrame()
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').tail(365)
        df = df.rename(columns={"open":"Open","high":"High","low":"Low","close":"Close","volume":"Volume"})
        df.index = df['date']
        cols = [c for c in ['Open','High','Low','Close','Volume'] if c in df.columns]
        return df[cols].dropna(subset=['Close'])
    except Exception:
        return pd.DataFrame()

def fetch_yfinance_data(symbol: str, market: str):
    try:
        import yfinance as yf
        yf_sym = f"{symbol}.SR" if market in ("sa","saudi","tasi") else symbol.upper()
        ticker = yf.Ticker(yf_sym)
        hist = ticker.history(period="1y")
        info = {}
        try: info = ticker.info or {}
        except: pass
        news = []
        try:
            for n in (ticker.news or [])[:8]:
                news.append({"title":n.get("title",""),"link":n.get("link",""),
                    "date":datetime.fromtimestamp(n.get("providerPublishTime",0)).strftime("%Y-%m-%d") if n.get("providerPublishTime") else ""})
        except: pass
        return hist, info, news
    except Exception:
        return pd.DataFrame(), {}, []

def get_stock_data(symbol: str, market: str) -> dict:
    result = {"hist":pd.DataFrame(),"info":{},"news":[],"price":None,"source":"none","error":None}
    hist_stooq = fetch_stooq(symbol, market)
    if not hist_stooq.empty and len(hist_stooq) >= 10:
        result["hist"] = hist_stooq
        result["price"] = float(hist_stooq['Close'].iloc[-1])
        result["source"] = "stooq"
    try:
        hist_yf, info_yf, news_yf = fetch_yfinance_data(symbol, market)
        if not hist_yf.empty and result["hist"].empty:
            result["hist"] = hist_yf
            result["source"] = "yfinance"
        live_price = info_yf.get("regularMarketPrice") or info_yf.get("currentPrice")
        if live_price:
            result["price"] = live_price
            result["source"] = "stooq+yfinance" if result["source"]=="stooq" else "yfinance"
        if info_yf: result["info"] = info_yf
        if news_yf: result["news"] = news_yf
    except: pass
    if result["hist"].empty:
        result["error"] = f"لم يُعثر على بيانات للرمز '{symbol}'."
    return result

# ═══════════════════════════════════════════════════════
# الحسابات الفنية
# ═══════════════════════════════════════════════════════

def safe(v):
    if v is None: return None
    try:
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else f
    except: return None

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, 1e-9)
    return 100 - (100 / (1 + rs))

def calculate_macd(series, fast=12, slow=26, signal=9):
    e1 = series.ewm(span=fast, adjust=False).mean()
    e2 = series.ewm(span=slow, adjust=False).mean()
    macd = e1 - e2
    sig = macd.ewm(span=signal, adjust=False).mean()
    return macd, sig, macd - sig

def calculate_bollinger(series, period=20, std_dev=2):
    mid = series.rolling(period).mean()
    std = series.rolling(period).std()
    return mid + std_dev * std, mid, mid - std_dev * std

def calculate_atr(high, low, close, period=14):
    tr = pd.concat([high-low,(high-close.shift()).abs(),(low-close.shift()).abs()],axis=1).max(axis=1)
    return tr.rolling(period).mean()

def calculate_stochastic(high, low, close, k=14, d=3):
    low_k = low.rolling(k).min()
    high_k = high.rolling(k).max()
    stoch_k = 100 * (close - low_k) / (high_k - low_k + 1e-9)
    return stoch_k, stoch_k.rolling(d).mean()

def calculate_obv(close, volume):
    direction = close.diff().apply(lambda x: 1 if x>0 else (-1 if x<0 else 0))
    return (direction * volume).cumsum()

def detect_support_resistance(df, window=20):
    highs = df['High'].rolling(window, center=True).max()
    lows  = df['Low'].rolling(window, center=True).min()
    curr  = df['Close'].iloc[-1]
    res = sorted([v for v in highs.dropna().unique() if v > curr])[:3]
    sup = sorted([v for v in lows.dropna().unique() if v < curr], reverse=True)[:3]
    return res, sup

def fibonacci_levels(df):
    high = df['High'].tail(60).max()
    low  = df['Low'].tail(60).min()
    diff = high - low
    return {
        "0%":    round(high, 3),
        "23.6%": round(high - 0.236*diff, 3),
        "38.2%": round(high - 0.382*diff, 3),
        "50%":   round(high - 0.500*diff, 3),
        "61.8%": round(high - 0.618*diff, 3),
        "78.6%": round(high - 0.786*diff, 3),
        "100%":  round(low, 3),
        # امتدادات
        "127.2%": round(low - 0.272*diff, 3),
        "161.8%": round(low - 0.618*diff, 3),
    }

def detect_trend(df, tech):
    """تحديد الاتجاه العام بدقة"""
    close = df['Close']
    s20 = safe(tech['sma20'].iloc[-1])
    s50 = safe(tech['sma50'].iloc[-1])
    s200 = safe(tech['sma200'].iloc[-1])
    curr = float(close.iloc[-1])

    # اتجاه قصير المدى (20 يوم)
    slope_20 = (close.iloc[-1] - close.iloc[-20]) / close.iloc[-20] * 100 if len(close) >= 20 else 0
    # اتجاه متوسط المدى (50 يوم)
    slope_50 = (close.iloc[-1] - close.iloc[-50]) / close.iloc[-50] * 100 if len(close) >= 50 else 0

    # تحديد الاتجاه
    points = 0
    if s20 and curr > s20: points += 2
    if s50 and curr > s50: points += 2
    if s200 and curr > s200: points += 1
    if s20 and s50 and s20 > s50: points += 2  # Golden Cross
    if slope_20 > 2: points += 1
    if slope_50 > 5: points += 1

    if points >= 6: trend = ("صاعد قوي 🚀", "#3fb950", "up_strong")
    elif points >= 4: trend = ("صاعد 📈", "#58a6ff", "up")
    elif points <= 1: trend = ("هابط قوي 📉", "#f85149", "down_strong")
    elif points <= 3: trend = ("هابط ⬇️", "#f0883e", "down")
    else: trend = ("عرضي ↔️", "#d29922", "sideways")

    return {
        "label": trend[0], "color": trend[1], "type": trend[2],
        "slope_20": round(slope_20, 2), "slope_50": round(slope_50, 2),
        "points": points
    }

def detect_accumulation_distribution(df, tech):
    """كشف مناطق التجميع والتصريف"""
    close = df['Close']
    volume = df['Volume'] if 'Volume' in df.columns else pd.Series(0, index=df.index)

    # Money Flow Index
    obv = tech['obv']
    obv_slope = (obv.iloc[-1] - obv.iloc[-20]) / abs(obv.iloc[-20]) * 100 if len(obv) >= 20 and obv.iloc[-20] != 0 else 0

    # نسبة الحجم المرتفع
    vol_avg = volume.rolling(20).mean().iloc[-1]
    vol_curr = volume.iloc[-1]
    vol_ratio = vol_curr / vol_avg if vol_avg > 0 else 1

    # A/D Line
    high = df['High']
    low  = df['Low']
    mfm = ((close - low) - (high - close)) / (high - low + 1e-9)
    ad = (mfm * volume).cumsum()
    ad_slope = (ad.iloc[-1] - ad.iloc[-20]) / abs(ad.iloc[-20]) * 100 if len(ad) >= 20 and ad.iloc[-20] != 0 else 0

    # Smart Money (حجم مرتفع + سعر يرتفع)
    price_up = close.iloc[-1] > close.iloc[-5] if len(close) >= 5 else True
    smart_money = vol_ratio > 1.5 and price_up

    if obv_slope > 5 and ad_slope > 0:
        phase = ("تجميع قوي 🟢", "#3fb950", 85)
    elif obv_slope > 0:
        phase = ("تجميع خفيف", "#58a6ff", 65)
    elif obv_slope < -5 and ad_slope < 0:
        phase = ("تصريف قوي 🔴", "#f85149", 20)
    elif obv_slope < 0:
        phase = ("تصريف خفيف", "#f0883e", 40)
    else:
        phase = ("محايد", "#d29922", 50)

    return {
        "phase": phase[0], "color": phase[1], "score": phase[2],
        "obv_slope": round(obv_slope, 2),
        "ad_slope": round(ad_slope, 2),
        "vol_ratio": round(vol_ratio, 2),
        "smart_money": smart_money
    }

def calculate_signal_confidence(signals, score, tech, df):
    """حساب نسبة نجاح الإشارة"""
    # عدد الإشارات المتوافقة
    buy_signals = sum(1 for s in signals.values() if s[2] > 0)
    sell_signals = sum(1 for s in signals.values() if s[2] < 0)
    total = len(signals)

    dominant = max(buy_signals, sell_signals)
    agreement_ratio = dominant / total if total > 0 else 0

    # عوامل إضافية
    rsi_v = safe(tech['rsi'].iloc[-1]) or 50
    macd_v = safe(tech['macd_hist'].iloc[-1]) or 0
    vol_ratio = 1.0
    if 'Volume' in df.columns:
        vol_curr = df['Volume'].iloc[-1]
        vol_avg = df['Volume'].rolling(20).mean().iloc[-1]
        vol_ratio = vol_curr / vol_avg if vol_avg > 0 else 1

    # حساب الثقة
    confidence = agreement_ratio * 60
    if vol_ratio > 1.5: confidence += 15
    if abs(rsi_v - 50) > 20: confidence += 10
    if abs(macd_v) > 0.01: confidence += 10
    confidence = min(95, max(30, confidence))

    return round(confidence)

def calculate_sector_comparison(price, info, score):
    """مقارنة السهم بالقطاع"""
    sector = info.get('sector', 'Unknown')
    pe = info.get('trailingPE')
    roe = info.get('returnOnEquity')
    margin = info.get('profitMargins')

    # متوسطات القطاعات
    sector_avgs = {
        'Energy':       {'pe': 12, 'roe': 0.18, 'margin': 0.15, 'avg_score': 60},
        'Financials':   {'pe': 14, 'roe': 0.12, 'margin': 0.25, 'avg_score': 58},
        'Technology':   {'pe': 28, 'roe': 0.22, 'margin': 0.22, 'avg_score': 65},
        'Healthcare':   {'pe': 22, 'roe': 0.15, 'margin': 0.18, 'avg_score': 62},
        'Consumer':     {'pe': 20, 'roe': 0.18, 'margin': 0.12, 'avg_score': 57},
        'Materials':    {'pe': 15, 'roe': 0.14, 'margin': 0.14, 'avg_score': 55},
        'الطاقة':       {'pe': 12, 'roe': 0.18, 'margin': 0.15, 'avg_score': 60},
        'البنوك':       {'pe': 13, 'roe': 0.12, 'margin': 0.30, 'avg_score': 58},
        'البتروكيماويات':{'pe': 15, 'roe': 0.14, 'margin': 0.14, 'avg_score': 55},
        'الاتصالات':    {'pe': 18, 'roe': 0.16, 'margin': 0.18, 'avg_score': 57},
    }
    avg = sector_avgs.get(sector, {'pe': 18, 'roe': 0.15, 'margin': 0.15, 'avg_score': 58})

    result = {
        'sector': sector,
        'sector_pe': avg['pe'],
        'sector_score': avg['avg_score'],
        'stock_score': score,
        'vs_sector': score - avg['avg_score'],
    }

    if pe and avg['pe']:
        result['pe_vs_sector'] = round((pe - avg['pe']) / avg['pe'] * 100, 1)
        result['pe_rating'] = "أرخص من القطاع ✅" if pe < avg['pe'] else "أغلى من القطاع ⚠️"
    else:
        result['pe_vs_sector'] = None
        result['pe_rating'] = "غير متاح"

    if result['vs_sector'] > 10:
        result['vs_label'] = ("أقوى من القطاع 🏆", "#3fb950")
    elif result['vs_sector'] > 0:
        result['vs_label'] = ("أعلى من المتوسط", "#58a6ff")
    elif result['vs_sector'] < -10:
        result['vs_label'] = ("أضعف من القطاع ⚠️", "#f85149")
    else:
        result['vs_label'] = ("في مستوى القطاع", "#d29922")

    return result

def analyze_technicals(df):
    close  = df['Close']
    high   = df['High']
    low    = df['Low']
    volume = df['Volume'] if 'Volume' in df.columns else pd.Series(0, index=df.index)

    rsi = calculate_rsi(close)
    macd, macd_sig, macd_hist = calculate_macd(close)
    bb_upper, bb_mid, bb_lower = calculate_bollinger(close)
    atr    = calculate_atr(high, low, close)
    stoch_k, stoch_d = calculate_stochastic(high, low, close)
    obv    = calculate_obv(close, volume)
    sma20  = close.rolling(20).mean()
    sma50  = close.rolling(50).mean()
    sma200 = close.rolling(200).mean()
    ema9   = close.ewm(span=9).mean()
    ema21  = close.ewm(span=21).mean()
    resistance, support = detect_support_resistance(df)
    fibs   = fibonacci_levels(df)

    return {
        "rsi":rsi,"macd":macd,"macd_sig":macd_sig,"macd_hist":macd_hist,
        "bb_upper":bb_upper,"bb_mid":bb_mid,"bb_lower":bb_lower,
        "atr":atr,"stoch_k":stoch_k,"stoch_d":stoch_d,
        "obv":obv,"sma20":sma20,"sma50":sma50,"sma200":sma200,
        "ema9":ema9,"ema21":ema21,
        "resistance":resistance,"support":support,"fibs":fibs,"volume":volume
    }

def detect_candlestick_patterns(df):
    patterns = []
    if len(df) < 3: return patterns
    opens=df['Open'].values; highs=df['High'].values
    lows=df['Low'].values; closes=df['Close'].values
    def body(i): return abs(closes[i]-opens[i])
    def rng(i): return highs[i]-lows[i]
    def upper(i): return highs[i]-max(opens[i],closes[i])
    def lower(i): return min(opens[i],closes[i])-lows[i]
    def bull(i): return closes[i]>opens[i]
    i=len(closes)-1
    if rng(i)>0 and body(i)/rng(i)<0.1:
        patterns.append({"name":"دوجي","type":"انعكاس محتمل","signal":"محايد","bullish":None,"strength":"متوسط"})
    if bull(i) and lower(i)>2*body(i) and upper(i)<0.1*rng(i) and body(i)>0:
        patterns.append({"name":"مطرقة ↑","type":"انعكاس صعودي","signal":"شراء","bullish":True,"strength":"قوي"})
    if not bull(i) and upper(i)>2*body(i) and lower(i)<0.1*rng(i) and body(i)>0:
        patterns.append({"name":"نجمة ساقطة ↓","type":"انعكاس هبوطي","signal":"بيع","bullish":False,"strength":"قوي"})
    if body(i)>0.85*rng(i) and bull(i):
        patterns.append({"name":"ماروبوزو صاعد ↑","type":"استمرار صعودي","signal":"شراء قوي","bullish":True,"strength":"قوي جداً"})
    if body(i)>0.85*rng(i) and not bull(i):
        patterns.append({"name":"ماروبوزو هابط ↓","type":"استمرار هبوطي","signal":"بيع قوي","bullish":False,"strength":"قوي جداً"})
    if i>=1:
        p=i-1
        if not bull(p) and bull(i) and closes[i]>opens[p] and opens[i]<closes[p]:
            patterns.append({"name":"ابتلاع شرائي ↑","type":"انعكاس صعودي","signal":"شراء قوي","bullish":True,"strength":"قوي جداً"})
        if bull(p) and not bull(i) and closes[i]<opens[p] and opens[i]>closes[p]:
            patterns.append({"name":"ابتلاع بيعي ↓","type":"انعكاس هبوطي","signal":"بيع قوي","bullish":False,"strength":"قوي جداً"})
    if i>=2:
        a,b,c=i-2,i-1,i
        if not bull(a) and body(b)<0.3*rng(b) and bull(c) and closes[c]>(opens[a]+closes[a])/2:
            patterns.append({"name":"نجمة الصباح ↑","type":"انعكاس صعودي","signal":"شراء قوي","bullish":True,"strength":"قوي جداً"})
        if bull(a) and body(b)<0.3*rng(b) and not bull(c) and closes[c]<(opens[a]+closes[a])/2:
            patterns.append({"name":"نجمة المساء ↓","type":"انعكاس هبوطي","signal":"بيع قوي","bullish":False,"strength":"قوي جداً"})
        if all(bull(x) and body(x)>0.6*rng(x) for x in [a,b,c]) and closes[a]<closes[b]<closes[c]:
            patterns.append({"name":"ثلاثة جنود بيض ↑","type":"استمرار صعودي","signal":"شراء قوي","bullish":True,"strength":"قوي جداً"})
        if all(not bull(x) and body(x)>0.6*rng(x) for x in [a,b,c]) and closes[a]>closes[b]>closes[c]:
            patterns.append({"name":"ثلاثة غربان سود ↓","type":"استمرار هبوطي","signal":"بيع قوي","bullish":False,"strength":"قوي جداً"})
    if not patterns:
        b_=closes[-1]>opens[-1]
        patterns.append({"name":"شمعة "+("صاعدة" if b_ else "هابطة"),"type":"استمرار","signal":"استمرار","bullish":b_,"strength":"ضعيف"})
    return patterns

def calculate_fair_value(price, info, tech):
    results = {}
    eps = info.get('trailingEps'); bvps = info.get('bookValue')
    if eps and bvps and eps>0 and bvps>0:
        results['graham'] = round((22.5*eps*bvps)**0.5, 3)
    else: results['graham'] = None
    pe=info.get('trailingPE'); eps2=info.get('trailingEps')
    if pe and eps2 and eps2>0:
        results['fair_pe'] = round(15*eps2, 3)
    else: results['fair_pe'] = None
    valid=[v for v in [results.get('graham'),results.get('fair_pe')] if v and v>0]
    results['avg_fair'] = round(sum(valid)/len(valid),3) if valid else None
    support=tech.get('support',[]); resistance=tech.get('resistance',[])
    entry_zones=[]
    if support:
        entry_zones.append({"zone":"منطقة شراء قوية","from":round(support[0]*0.99,3),"to":round(support[0]*1.01,3),"type":"دعم رئيسي"})
    if len(support)>1:
        entry_zones.append({"zone":"منطقة شراء ممتازة","from":round(support[1]*0.99,3),"to":round(support[1]*1.01,3),"type":"دعم ثانوي"})
    sell_zones=[]
    if resistance:
        sell_zones.append({"zone":"منطقة بيع/جني أرباح","from":round(resistance[0]*0.99,3),"to":round(resistance[0]*1.01,3),"type":"مقاومة رئيسية"})
    results['entry_zones']=entry_zones; results['sell_zones']=sell_zones
    if results['avg_fair']:
        margin=(results['avg_fair']-price)/price*100
        if margin>20: results['valuation']=("مقيَّم بأقل من قيمته ✅","#3fb950",margin)
        elif margin>5: results['valuation']=("يقترب من قيمته العادلة","#d29922",margin)
        elif margin<-20: results['valuation']=("مقيَّم بأكثر من قيمته ⚠️","#f85149",margin)
        else: results['valuation']=("عند قيمته العادلة","#58a6ff",margin)
    else: results['valuation']=None
    return results

def generate_signals(df, tech):
    close=df['Close']; curr=float(close.iloc[-1])
    signals={}; score=50
    rsi_v=safe(tech['rsi'].iloc[-1])
    if rsi_v is not None:
        if rsi_v<25:   signals['RSI']=('تشبع بيعي شديد ✅','b-green',+18)
        elif rsi_v<35: signals['RSI']=('تشبع بيعي ✅','b-green',+12)
        elif rsi_v<45: signals['RSI']=('ميل شراء','b-green',+5)
        elif rsi_v>80: signals['RSI']=('تشبع شرائي شديد ⚠️','b-red',-18)
        elif rsi_v>70: signals['RSI']=('تشبع شرائي ⚠️','b-red',-12)
        elif rsi_v>60: signals['RSI']=('ميل بيع','b-red',-5)
        else:          signals['RSI']=('محايد','b-yellow',0)
    mh=safe(tech['macd_hist'].iloc[-1]); mp=safe(tech['macd_hist'].iloc[-2]) if len(tech['macd_hist'])>1 else mh
    if mh is not None and mp is not None:
        if mh>0 and mh>mp:   signals['MACD']=('تقاطع صاعد ✅','b-green',+15)
        elif mh>0:            signals['MACD']=('إيجابي','b-green',+7)
        elif mh<0 and mh<mp: signals['MACD']=('تقاطع هابط ⚠️','b-red',-15)
        else:                 signals['MACD']=('سلبي','b-red',-7)
    bbu=safe(tech['bb_upper'].iloc[-1]); bbl=safe(tech['bb_lower'].iloc[-1])
    if bbu and bbl:
        if curr<bbl*0.99:   signals['بولينجر']=('تحت النطاق - شراء ✅','b-green',+12)
        elif curr<bbl:      signals['بولينجر']=('عند الدعم','b-green',+6)
        elif curr>bbu*1.01: signals['بولينجر']=('فوق النطاق - بيع ⚠️','b-red',-12)
        elif curr>bbu:      signals['بولينجر']=('عند المقاومة','b-red',-6)
        else:               signals['بولينجر']=('ضمن النطاق','b-yellow',0)
    s20=safe(tech['sma20'].iloc[-1]); s50=safe(tech['sma50'].iloc[-1]); s200=safe(tech['sma200'].iloc[-1])
    if s20 and s50:
        if curr>s20 and curr>s50 and s20>s50 and (s200 is None or curr>s200):
            signals['المتوسطات']=('فوق الكل - صاعد قوي ✅','b-green',+15)
        elif curr>s20 and curr>s50: signals['المتوسطات']=('فوق SMA20 و50 ✅','b-green',+8)
        elif curr<s20 and curr<s50: signals['المتوسطات']=('تحت SMA20 و50 ⚠️','b-red',-8)
        else: signals['المتوسطات']=('مختلط','b-yellow',0)
    sk=safe(tech['stoch_k'].iloc[-1])
    if sk is not None:
        if sk<20:   signals['ستوكاستك']=('تشبع بيعي ✅','b-green',+10)
        elif sk>80: signals['ستوكاستك']=('تشبع شرائي ⚠️','b-red',-10)
        else:       signals['ستوكاستك']=('محايد','b-yellow',0)
    if 'Volume' in df.columns:
        vol_curr=df['Volume'].iloc[-1]; vol_avg=df['Volume'].rolling(20).mean().iloc[-1]
        if vol_curr>vol_avg*1.5:   signals['الحجم']=('ارتفاع في الحجم ✅','b-green',+8)
        elif vol_curr<vol_avg*0.5: signals['الحجم']=('انخفاض في الحجم','b-yellow',-3)
        else:                      signals['الحجم']=('حجم طبيعي','b-yellow',0)
    for sig in signals.values(): score+=sig[2]
    score=max(5,min(95,score))
    if   score>=78: verdict=('شراء قوي','v-strong-buy','#3fb950')
    elif score>=62: verdict=('شراء','v-buy','#58a6ff')
    elif score>=45: verdict=('احتفاظ','v-hold','#d29922')
    elif score>=32: verdict=('تخفيض','v-reduce','#f0883e')
    else:           verdict=('بيع','v-sell','#f85149')
    atr_v=safe(tech['atr'].iloc[-1]) or curr*0.02
    resistance=tech['resistance']; support=tech['support']
    stop_loss=round(support[0]*0.99,3) if support else round(curr*0.95,3)
    t1=round(resistance[0],3) if resistance else round(curr*1.05,3)
    t2=round(resistance[1],3) if len(resistance)>1 else round(curr*1.10,3)
    t3=round(curr*1.15,3)
    rr=round((t2-curr)/(curr-stop_loss),1) if curr>stop_loss else 1.0
    import math as _math
    def _safe_days(dist, default):
        try:
            v = float(dist)
            if _math.isnan(v) or _math.isinf(v) or v == 0: return default
            return max(default, int(abs(v) / 0.3))
        except: return default
    def _safe_dist(a, b, c):
        try:
            if not c or c == 0: return 1.0
            v = round((a - b) / c * 100, 1)
            if _math.isnan(v) or _math.isinf(v): return 1.0
            return v
        except: return 1.0
    dist_t1 = _safe_dist(t1, curr, curr)
    dist_t2 = _safe_dist(t2, curr, curr)
    days_t1 = _safe_days(dist_t1, 10)
    days_t2 = _safe_days(dist_t2, 20)
    return signals, score, verdict, {
        "stop_loss":stop_loss,"t1":t1,"t2":t2,"t3":t3,
        "rr":rr,"atr":atr_v,
        "dist_t1":dist_t1,"dist_t2":dist_t2,
        "days_t1":days_t1,"days_t2":days_t2
    }

# ═══════════════════════════════════════════════════════
# الأخبار
# ═══════════════════════════════════════════════════════

POSITIVE_KW=["profit","growth","record","increase","beat","strong","buy","upgrade","dividend","ربح","نمو","ارتفاع","قوي","شراء","توزيعات","تطور","نجاح","زيادة"]
NEGATIVE_KW=["loss","decline","miss","weak","downgrade","sell","lawsuit","cut","warning","خسارة","انخفاض","ضعف","بيع","تراجع","قضية","غرامة","تحقيق"]

def analyze_news_sentiment(news):
    if not news: return {"score":50,"sentiment":"محايد","items":[],"pos":0,"neg":0,"neu":0}
    analyzed=[]; pos=neg=neu=0
    for item in news:
        text=(item.get("title","")+item.get("summary","")).lower()
        ph=sum(1 for k in POSITIVE_KW if k in text)
        nh=sum(1 for k in NEGATIVE_KW if k in text)
        if ph>nh: s="إيجابي"; pos+=1
        elif nh>ph: s="سلبي"; neg+=1
        else: s="محايد"; neu+=1
        analyzed.append({**item,"sentiment":s})
    score=round(50+(pos-neg)/len(news)*45)
    score=max(10,min(90,score))
    overall="إيجابي" if score>=60 else "سلبي" if score<=40 else "محايد"
    return {"score":score,"sentiment":overall,"pos":pos,"neg":neg,"neu":neu,"items":analyzed}

# ═══════════════════════════════════════════════════════
# التوقعات السعرية
# ═══════════════════════════════════════════════════════

def predict_price_targets(price, tech, info, score):
    atr=safe(tech['atr'].iloc[-1]) or price*0.02
    resistance=tech.get('resistance',[]); support=tech.get('support',[]); fibs=tech.get('fibs',{})
    targets_up=[]
    if resistance:
        for i,r in enumerate(resistance[:3]):
            diff_pct=(r-price)/price*100
            days=max(5,int(abs(diff_pct)/0.3))
            targets_up.append({"price":round(r,3),"pct":round(diff_pct,1),"days":days,"type":"مقاومة","probability":max(30,80-i*15)})
    atr_target=round(price+2*atr,3)
    targets_up.append({"price":atr_target,"pct":round((atr_target-price)/price*100,1),"days":14,"type":"ATR×2","probability":60})
    fib_above={k:v for k,v in fibs.items() if v>price and "%" not in k.replace(".","").replace("%","")}
    if fib_above:
        nfl=min(fib_above.items(),key=lambda x:x[1])
        targets_up.append({"price":round(nfl[1],3),"pct":round((nfl[1]-price)/price*100,1),"days":max(7,int(abs((nfl[1]-price)/price*100/0.25))),"type":f"فيب {nfl[0]}","probability":65})
    targets_down=[]
    if support:
        for s in support[:2]:
            targets_down.append({"price":round(s,3),"pct":round((s-price)/price*100,1),"type":"دعم/وقف","probability":70})
    targets_up=sorted([t for t in targets_up if t['pct']>0],key=lambda x:x['price'])[:4]
    return targets_up, targets_down

def generate_scenarios(price, tech, score, targets_up, targets_down):
    """توليد السيناريو الإيجابي والسلبي والنطاق المتوقع"""
    atr=safe(tech['atr'].iloc[-1]) or price*0.02
    resistance=tech.get('resistance',[]); support=tech.get('support',[])

    # السيناريو الإيجابي
    pos_t1=targets_up[0]['price'] if targets_up else round(price*1.05,3)
    pos_t2=targets_up[1]['price'] if len(targets_up)>1 else round(price*1.10,3)
    pos_prob=65 if score>=60 else 45

    # السيناريو السلبي
    neg_t1=targets_down[0]['price'] if targets_down else round(price*0.97,3)
    neg_t2=targets_down[1]['price'] if len(targets_down)>1 else round(price*0.94,3)
    neg_prob=100-pos_prob

    # النطاق المتوقع (أسبوع)
    weekly_high=round(price+atr*2,3)
    weekly_low=round(price-atr*2,3)

    # أقرب دعم ومقاومة
    nearest_res=resistance[0] if resistance else round(price*1.03,3)
    nearest_sup=support[0] if support else round(price*0.97,3)

    return {
        "positive":{"t1":pos_t1,"t2":pos_t2,"prob":pos_prob,"label":"سيناريو إيجابي 🟢"},
        "negative":{"t1":neg_t1,"t2":neg_t2,"prob":neg_prob,"label":"سيناريو سلبي 🔴"},
        "weekly_range":{"high":weekly_high,"low":weekly_low},
        "nearest_res":nearest_res,"nearest_sup":nearest_sup
    }

# ═══════════════════════════════════════════════════════
# الرسم البياني المحسّن
# ═══════════════════════════════════════════════════════

def build_chart(df, tech, symbol, targets, show_vol=True, candles_patterns=None):
    rows=4 if show_vol else 3
    heights=[0.52,0.18,0.15,0.15] if show_vol else [0.58,0.22,0.20]

    fig=make_subplots(rows=rows,cols=1,shared_xaxes=True,vertical_spacing=0.02,
        row_heights=heights,
        subplot_titles=("","RSI","MACD","حجم التداول") if show_vol else ("","RSI","MACD"))

    price=float(df['Close'].iloc[-1])

    # ── ملخص سريع أعلى الشارت ─────────────────────────
    # (يُعرض كـ annotation)
    rsi_v=safe(tech['rsi'].iloc[-1]) or 50
    trend_info=detect_trend(df,tech)
    summary_text=f"📊 {symbol} | اتجاه: {trend_info['label']} | RSI: {rsi_v:.0f} | سعر الدخول: {targets['stop_loss']:.2f}→{targets['t1']:.2f}"

    # شموع يابانية
    fig.add_trace(go.Candlestick(
        x=df.index,open=df['Open'],high=df['High'],low=df['Low'],close=df['Close'],name="السعر",
        increasing=dict(line=dict(color='#3fb950',width=1),fillcolor='#3fb950'),
        decreasing=dict(line=dict(color='#f85149',width=1),fillcolor='#f85149'),
    ),row=1,col=1)

    # المتوسطات
    for nm,clr,w in [('sma20','#58a6ff',1.5),('sma50','#d29922',1.5),('sma200','#f0883e',1)]:
        val=tech.get(nm)
        if val is not None and not val.isna().all():
            fig.add_trace(go.Scatter(x=df.index,y=val,name=nm.upper(),line=dict(color=clr,width=w)),row=1,col=1)

    # بولينجر
    if not tech['bb_upper'].isna().all():
        fig.add_trace(go.Scatter(x=df.index,y=tech['bb_upper'],name='BB↑',line=dict(color='#bc8cff',width=1,dash='dash')),row=1,col=1)
        fig.add_trace(go.Scatter(x=df.index,y=tech['bb_lower'],name='BB↓',line=dict(color='#bc8cff',width=1,dash='dash'),fill='tonexty',fillcolor='rgba(188,140,255,0.05)'),row=1,col=1)

    # ── خطوط الدعم والمقاومة المُحسَّنة ──────────────────
    for i,r in enumerate(tech['resistance'][:3]):
        if r:
            fig.add_hline(y=r,line=dict(color='#f85149',width=1.5 if i==0 else 1,dash='solid' if i==0 else 'dot'),
                annotation_text=f"مقاومة {i+1}: {r:.2f}",annotation_position="right",
                annotation_font=dict(color='#f85149',size=10),row=1,col=1)

    for i,s in enumerate(tech['support'][:3]):
        if s:
            fig.add_hline(y=s,line=dict(color='#3fb950',width=1.5 if i==0 else 1,dash='solid' if i==0 else 'dot'),
                annotation_text=f"دعم {i+1}: {s:.2f}",annotation_position="right",
                annotation_font=dict(color='#3fb950',size=10),row=1,col=1)

    # ── الأهداف السعرية على الشارت ───────────────────────
    t1=targets.get('t1'); t2=targets.get('t2'); sl=targets.get('stop_loss')
    if t1 and t1>price:
        fig.add_hline(y=t1,line=dict(color='#58a6ff',width=1.5,dash='dash'),
            annotation_text=f"🎯 هدف 1: {t1:.2f}",annotation_position="left",
            annotation_font=dict(color='#58a6ff',size=10),row=1,col=1)
    if t2 and t2>price:
        fig.add_hline(y=t2,line=dict(color='#bc8cff',width=1.5,dash='dash'),
            annotation_text=f"🎯 هدف 2: {t2:.2f}",annotation_position="left",
            annotation_font=dict(color='#bc8cff',size=10),row=1,col=1)
    if sl:
        fig.add_hline(y=sl,line=dict(color='#f85149',width=1.5,dash='dashdot'),
            annotation_text=f"🛑 وقف: {sl:.2f}",annotation_position="left",
            annotation_font=dict(color='#f85149',size=10),row=1,col=1)

    # ── علامات الشراء والبيع والأهداف على الشارت ──────────
    last_date = df.index[-1]
    last_high = float(df['High'].iloc[-1])
    last_low  = float(df['Low'].iloc[-1])
    price_now = float(df['Close'].iloc[-1])

    # ── إشارة الشراء/البيع من الشموع ─────────────────────
    if candles_patterns:
        last_candle = candles_patterns[0]
        if last_candle.get('bullish') == True:
            fig.add_trace(go.Scatter(
                x=[last_date], y=[last_low * 0.992],
                mode='markers+text',
                marker=dict(symbol='triangle-up', size=22, color='#3fb950',
                    line=dict(color='#ffffff', width=1)),
                text=[f"🟢 شراء"], textposition='bottom center',
                textfont=dict(color='#3fb950', size=11, family='Cairo'),
                name='إشارة شراء', showlegend=True
            ), row=1, col=1)
        elif last_candle.get('bullish') == False:
            fig.add_trace(go.Scatter(
                x=[last_date], y=[last_high * 1.008],
                mode='markers+text',
                marker=dict(symbol='triangle-down', size=22, color='#f85149',
                    line=dict(color='#ffffff', width=1)),
                text=[f"🔴 بيع"], textposition='top center',
                textfont=dict(color='#f85149', size=11, family='Cairo'),
                name='إشارة بيع', showlegend=True
            ), row=1, col=1)

    # ── سهم الهدف 1 ───────────────────────────────────────
    t1 = targets.get('t1')
    t2 = targets.get('t2')
    sl = targets.get('stop_loss')

    if t1 and t1 > price_now:
        # خط أفقي + نص الهدف
        fig.add_annotation(
            x=df.index[int(len(df)*0.75)], y=t1,
            text=f"🎯 هدف 1: {t1:.2f}",
            showarrow=True, arrowhead=2, arrowsize=1.5,
            arrowcolor='#58a6ff', arrowwidth=2,
            ax=0, ay=-35,
            font=dict(color='#58a6ff', size=11, family='Cairo'),
            bgcolor='rgba(22,27,34,0.85)', bordercolor='#58a6ff',
            borderwidth=1, borderpad=4, row=1, col=1
        )

    if t2 and t2 > price_now:
        fig.add_annotation(
            x=df.index[int(len(df)*0.5)], y=t2,
            text=f"🎯 هدف 2: {t2:.2f}",
            showarrow=True, arrowhead=2, arrowsize=1.5,
            arrowcolor='#bc8cff', arrowwidth=2,
            ax=0, ay=-35,
            font=dict(color='#bc8cff', size=11, family='Cairo'),
            bgcolor='rgba(22,27,34,0.85)', bordercolor='#bc8cff',
            borderwidth=1, borderpad=4, row=1, col=1
        )

    if sl:
        fig.add_annotation(
            x=df.index[int(len(df)*0.6)], y=sl,
            text=f"🛑 وقف: {sl:.2f}",
            showarrow=True, arrowhead=2, arrowsize=1.5,
            arrowcolor='#f85149', arrowwidth=2,
            ax=0, ay=35,
            font=dict(color='#f85149', size=11, family='Cairo'),
            bgcolor='rgba(22,27,34,0.85)', bordercolor='#f85149',
            borderwidth=1, borderpad=4, row=1, col=1
        )

    # ── أسهم المقاومة ─────────────────────────────────────
    for i, r in enumerate(tech['resistance'][:2]):
        if r:
            fig.add_annotation(
                x=df.index[-5], y=r,
                text=f"⬆️ مقاومة {i+1}: {r:.2f}",
                showarrow=False,
                font=dict(color='#f85149', size=10, family='Cairo'),
                bgcolor='rgba(248,81,73,0.15)', bordercolor='#f85149',
                borderwidth=1, borderpad=3,
                xanchor='right', row=1, col=1
            )

    # ── أسهم الدعم ────────────────────────────────────────
    for i, s in enumerate(tech['support'][:2]):
        if s:
            fig.add_annotation(
                x=df.index[-5], y=s,
                text=f"⬇️ دعم {i+1}: {s:.2f}",
                showarrow=False,
                font=dict(color='#3fb950', size=10, family='Cairo'),
                bgcolor='rgba(63,185,80,0.15)', bordercolor='#3fb950',
                borderwidth=1, borderpad=3,
                xanchor='right', row=1, col=1
            )

    # ── منطقة الدخول المثالية (تظليل) ────────────────────
    if tech['support']:
        s = tech['support'][0]
        fig.add_hrect(y0=s*0.99, y1=s*1.01,
            fillcolor='rgba(63,185,80,0.1)', line_width=0, row=1, col=1)
        fig.add_annotation(
            x=df.index[int(len(df)*0.15)], y=s,
            text="✅ منطقة شراء",
            showarrow=False,
            font=dict(color='#3fb950', size=10, family='Cairo'),
            bgcolor='rgba(63,185,80,0.2)', bordercolor='#3fb950',
            borderwidth=1, borderpad=3, row=1, col=1
        )

    # RSI
    fig.add_trace(go.Scatter(x=df.index,y=tech['rsi'],name='RSI',line=dict(color='#58a6ff',width=2)),row=2,col=1)
    fig.add_hline(y=70,line=dict(color='#f85149',width=1,dash='dot'),row=2,col=1)
    fig.add_hline(y=30,line=dict(color='#3fb950',width=1,dash='dot'),row=2,col=1)
    fig.add_hline(y=50,line=dict(color='#8b949e',width=0.5,dash='dot'),row=2,col=1)
    fig.add_hrect(y0=70,y1=100,fillcolor='rgba(248,81,73,0.07)',line_width=0,row=2,col=1)
    fig.add_hrect(y0=0,y1=30,fillcolor='rgba(63,185,80,0.07)',line_width=0,row=2,col=1)

    # MACD
    colors_m=['#3fb950' if v>=0 else '#f85149' for v in tech['macd_hist'].fillna(0)]
    fig.add_trace(go.Bar(x=df.index,y=tech['macd_hist'],name='Hist',marker_color=colors_m,opacity=0.7),row=3,col=1)
    fig.add_trace(go.Scatter(x=df.index,y=tech['macd'],name='MACD',line=dict(color='#58a6ff',width=1.5)),row=3,col=1)
    fig.add_trace(go.Scatter(x=df.index,y=tech['macd_sig'],name='Signal',line=dict(color='#f0883e',width=1.5)),row=3,col=1)

    # حجم التداول
    if show_vol and 'Volume' in df.columns:
        vc=['#3fb950' if df['Close'].iloc[i]>=df['Open'].iloc[i] else '#f85149' for i in range(len(df))]
        fig.add_trace(go.Bar(x=df.index,y=df['Volume'],name='الحجم',marker_color=vc,opacity=0.6),row=4,col=1)

    fig.update_layout(
        title=dict(text=summary_text,font=dict(color='#8b949e',size=11,family='Cairo'),x=0.5),
        paper_bgcolor='#0d1117',plot_bgcolor='#0d1117',
        font=dict(color='#e6edf3',family='Cairo'),
        height=850,margin=dict(l=5,r=85,t=55,b=10),
        legend=dict(orientation='h',y=1.07,x=0,bgcolor='rgba(22,27,34,0.9)',
            bordercolor='#30363d',borderwidth=1,font=dict(size=10),
            itemwidth=40,tracegroupgap=0),
        xaxis_rangeslider_visible=False,hovermode='x unified',
        # تحسين الشموع للموبايل
        newshape=dict(line_color='#58a6ff'),
    )
    for i in range(1,rows+1):
        ax='xaxis' if i==1 else f'xaxis{i}'
        ya='yaxis' if i==1 else f'yaxis{i}'
        fig.update_layout(**{
            ax:dict(gridcolor='#21262d',gridwidth=0.5,showgrid=True,zeroline=False,
                tickfont=dict(size=10),showspikes=True,spikecolor='#58a6ff',spikethickness=1),
            ya:dict(gridcolor='#21262d',gridwidth=0.5,showgrid=True,zeroline=False,
                side='right',tickfont=dict(size=10),showspikes=True,spikecolor='#58a6ff'),
        })
    fig.update_layout(yaxis2=dict(range=[0,100]))
    # تكبير الشموع
    fig.update_traces(selector=dict(type='candlestick'),
        increasing_line_width=2, decreasing_line_width=2)
    return fig

# ═══════════════════════════════════════════════════════
# تقرير AI
# ═══════════════════════════════════════════════════════

def generate_ai_analysis(symbol,price,currency,score,verdict_text,signals,tech,info,news_sent,api_key):
    if not api_key:
        return _smart_report(symbol,price,currency,score,verdict_text,signals,tech,info,news_sent)
    rsi_v=safe(tech['rsi'].iloc[-1]) or 50
    macd_v=safe(tech['macd_hist'].iloc[-1]) or 0
    s20=safe(tech['sma20'].iloc[-1]); s50=safe(tech['sma50'].iloc[-1])
    resistance=tech.get('resistance',[]); support=tech.get('support',[])
    prompt=f"""أنت محلل مالي خبير. حلّل السهم {symbol} بدقة واحترافية.
السعر: {price:.3f} {currency} | القطاع: {info.get('sector','—')} | درجة التحليل: {score}/100
RSI: {rsi_v:.1f} | MACD: {macd_v:.4f} | SMA20: {f"{s20:.3f}" if s20 else "—"}
المقاومة: {f"{resistance[0]:.3f}" if resistance else "—"} | الدعم: {f"{support[0]:.3f}" if support else "—"}
التوصية: {verdict_text}

قدّم تقريراً شاملاً يتضمن: الملخص التنفيذي، التوقعات السعرية (أسبوع/شهر/3أشهر)، أهداف الصعود، وقف الخسارة، المحفزات، المخاطر، السيناريو الإيجابي والسلبي، التوصية النهائية مع مبررها بالأرقام."""
    try:
        resp=requests.post("https://api.anthropic.com/v1/messages",
            headers={"Content-Type":"application/json","x-api-key":api_key,"anthropic-version":"2023-06-01"},
            json={"model":"claude-sonnet-4-6","max_tokens":2000,
                  "system":"أنت محلل مالي خبير. أجب بالعربية فقط بشكل مفصل واحترافي.",
                  "messages":[{"role":"user","content":prompt}]},timeout=35)
        resp.raise_for_status()
        return resp.json()["content"][0]["text"]
    except Exception:
        return _smart_report(symbol,price,currency,score,verdict_text,signals,tech,info,news_sent)

def _smart_report(symbol,price,currency,score,verdict_text,signals,tech,info,news_sent):
    rsi_v=safe(tech['rsi'].iloc[-1]) or 50
    macd_v=safe(tech['macd_hist'].iloc[-1]) or 0
    s20=safe(tech['sma20'].iloc[-1]); s50=safe(tech['sma50'].iloc[-1])
    atr_v=safe(tech['atr'].iloc[-1]) or price*0.02
    res=tech.get('resistance',[]); sup=tech.get('support',[])
    catalysts=[]; risks=[]
    if rsi_v<35: catalysts.append(f"RSI={rsi_v:.1f} في منطقة تشبع بيعي — فرصة دخول")
    if macd_v>0: catalysts.append(f"MACD إيجابي ({macd_v:.4f}) — زخم صاعد")
    if s20 and price>s20: catalysts.append(f"السعر فوق SMA20 ({s20:.3f})")
    if s50 and price>s50: catalysts.append(f"السعر فوق SMA50 ({s50:.3f})")
    if sup: catalysts.append(f"دعم قوي عند {sup[0]:.3f}")
    if rsi_v>70: risks.append(f"RSI={rsi_v:.1f} تشبع شرائي")
    if macd_v<0: risks.append(f"MACD سلبي ({macd_v:.4f})")
    if s20 and price<s20: risks.append(f"السعر تحت SMA20 ({s20:.3f})")
    if res: risks.append(f"مقاومة عند {res[0]:.3f}")
    if not catalysts: catalysts=["مؤشرات في مستوى مقبول","إمكانية تحسن","قوة السوق"]
    if not risks: risks=["مخاطر السوق العامة","تقلبات طبيعية","عدم اليقين"]
    tw=round(price+atr_v*1.5,3); tm=round(price+atr_v*3,3); t3m=round(price+atr_v*6,3)
    sl=round(sup[0]*0.985,3) if sup else round(price*0.95,3)
    if score<45: tw=round(price-atr_v*1.5,3); tm=round(price-atr_v*2.5,3); t3m=round(price-atr_v*4,3)
    t1p=round(res[0],3) if res else tw
    t2p=round(res[1],3) if len(res)>1 else tm
    t3p=round(price*(1.15 if score>=60 else 0.88),3)
    trend="صاعد" if s20 and price>s20 else "هابط" if s20 else "جانبي"
    nc="إيجابية" if news_sent.get('score',50)>=60 else "سلبية" if news_sent.get('score',50)<=40 else "محايدة"
    return f"""## 📊 تقرير التحليل الذكي — {symbol}

### الملخص التنفيذي
سهم **{symbol}** بدرجة **{score}/100** — توصية **{verdict_text}** — اتجاه **{trend}**.
السعر الحالي {price:.3f} {currency} | الأخبار {nc} ({news_sent.get('score',50)}/100).

---

### 📈 التوقعات السعرية
| الفترة | السعر المتوقع | التغير |
|--------|--------------|--------|
| أسبوع | **{tw:.3f} {currency}** | {(tw-price)/price*100:+.1f}% |
| شهر | **{tm:.3f} {currency}** | {(tm-price)/price*100:+.1f}% |
| 3 أشهر | **{t3m:.3f} {currency}** | {(t3m-price)/price*100:+.1f}% |

### 🎯 أهداف الصعود
- **الهدف 1:** {t1p:.3f} ({(t1p-price)/price*100:+.1f}%) — {'مقاومة رئيسية' if res else 'ATR'}
- **الهدف 2:** {t2p:.3f} ({(t2p-price)/price*100:+.1f}%)
- **الهدف 3:** {t3p:.3f} ({(t3p-price)/price*100:+.1f}%)

### 🛑 وقف الخسارة: {sl:.3f} ({(sl-price)/price*100:+.1f}%)

### السيناريو الإيجابي 🟢 (احتمالية {65 if score>=60 else 45}%)
السعر يكسر {t1p:.3f} ويصل {t2p:.3f} خلال {max(5,int(abs((t2p-price)/price*100/0.3)))} جلسة.

### السيناريو السلبي 🔴 (احتمالية {35 if score>=60 else 55}%)
الكسر تحت {sl:.3f} قد يصل {round(sl*0.97,3):.3f}.

### النطاق الأسبوعي المتوقع: {round(price-atr_v*2,3):.3f} ← {round(price+atr_v*2,3):.3f}

### ✅ المحفزات
{chr(10).join([f'- {c}' for c in catalysts[:4]])}

### ⚠️ المخاطر
{chr(10).join([f'- {r}' for r in risks[:4]])}

### 📋 التوصية النهائية
**{verdict_text}** (درجة ثقة {score}%) | نسبة مخاطرة/عائد: 1:{round((t2p-price)/(price-sl),1) if price>sl else 1}
{'دخول مثالي: ' + str(sup[0]) + ' — ' + str(round(sup[0]*1.01,3)) if sup and score>=60 else 'انتظار تأكيد الاتجاه.'}
"""

# ═══════════════════════════════════════════════════════
# الواجهة الرئيسية
# ═══════════════════════════════════════════════════════

st.markdown("""
<div class="pro-header">
  <h1>📊 محلل الأسهم الذكي Pro v3</h1>
  <p>محفظة • تنبيهات • أخبار • AI • تحليل شامل • 10 أسواق عالمية • بيانات لحظية</p>
</div>
""", unsafe_allow_html=True)

nav=st.radio("",["🔍 تحليل","⚖️ مقارنة","💼 المحفظة","🔔 التنبيهات","👁️ المراقبة","📜 السجل"],
    horizontal=True,label_visibility="collapsed")
st.divider()

MARKETS={"🇸🇦 السوق السعودي (TASI)":"sa","🇺🇸 الأمريكي (NYSE/NASDAQ)":"us",
    "🇦🇪 الإماراتي (DFM/ADX)":"ae","🇶🇦 القطري (QE)":"qa","🇰🇼 الكويتي":"kw",
    "🇧🇭 البحريني":"bh","🇯🇴 الأردني":"jo","🇪🇬 المصري (EGX)":"eg",
    "🇬🇧 البريطاني (LSE)":"gb","🇩🇪 الألماني (XETRA)":"de"}

if nav=="🔍 تحليل":
    with st.sidebar:
        st.markdown("### ⚙️ الإعدادات")
        api_key=st.text_input("🤖 مفتاح Claude AI (اختياري)",type="password",placeholder="sk-ant-...")
        show_vol=st.checkbox("عرض حجم التداول",value=True)
        st.markdown("---")
        st.markdown("### 📌 قائمة المراقبة")
        if 'watchlist' not in st.session_state:
            st.session_state.watchlist=[("2222","sa"),("1120","sa"),("AAPL","us")]
        for sym,mkt in st.session_state.watchlist:
            if st.button(f"📈 {sym}",key=f"wl_{sym}"):
                st.session_state['q_sym']=sym; st.session_state['q_mkt']=mkt; st.rerun()

    col_sym,col_mkt,col_btn=st.columns([3,2,1])
    with col_sym:
        symbol=st.text_input("🔍 رمز السهم",placeholder="مثال: 2222 أو AAPL",label_visibility="collapsed").strip().upper()
    with col_mkt:
        market_label=st.selectbox("السوق",list(MARKETS.keys()),label_visibility="collapsed")
        market=MARKETS[market_label]
    with col_btn:
        analyze=st.button("📊 تحليل السهم",use_container_width=True)

    st.markdown("**⚡ أسهم سريعة:**")
    qcols=st.columns(10)
    quick=[("2222","sa"),("1120","sa"),("7010","sa"),("2010","sa"),("1010","sa"),
           ("AAPL","us"),("NVDA","us"),("TSLA","us"),("MSFT","us"),("AMZN","us")]
    for i,(sym,mkt) in enumerate(quick):
        with qcols[i]:
            if st.button(sym,key=f"q_{sym}"):
                st.session_state['q_sym']=sym; st.session_state['q_mkt']=mkt; st.rerun()

    if 'q_sym' in st.session_state:
        symbol=st.session_state.pop('q_sym'); market=st.session_state.pop('q_mkt','sa'); analyze=True

    if analyze and symbol:
        with st.spinner(f"⏳ جاري تحليل {symbol}..."):
            data=get_stock_data(symbol,market)
        if data['error']:
            st.error(f"❌ {data['error']}"); st.stop()

        df=data['hist']; info=data['info']; news=data['news']
        price=data['price'] or float(df['Close'].iloc[-1]); source=data['source']
        prev=float(df['Close'].iloc[-2]) if len(df)>1 else price
        change=price-prev; chg_pct=(change/prev*100) if prev else 0
        name=info.get('longName') or info.get('shortName') or symbol
        currency=info.get('currency','SAR' if market=='sa' else 'USD')

        tech=analyze_technicals(df)
        signals,score,verdict,targets=generate_signals(df,tech)
        news_sent=analyze_news_sentiment(news)
        candles=detect_candlestick_patterns(df)
        fair_val=calculate_fair_value(price,info,tech)
        trend_info=detect_trend(df,tech)
        accum_info=detect_accumulation_distribution(df,tech)
        sector_cmp=calculate_sector_comparison(price,info,score)
        confidence=calculate_signal_confidence(signals,score,tech,df)
        targets_up,targets_down=predict_price_targets(price,tech,info,score)
        scenarios=generate_scenarios(price,tech,score,targets_up,targets_down)

        # ── Header ──────────────────────────────────────────
        up=change>=0
        st.markdown(f"""
        <div class="card">
          <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:1rem">
            <div>
              <div style="font-size:1.4rem;font-weight:900">{name}</div>
              <div style="color:#8b949e;font-size:.85rem">{symbol} · {market_label.split('(')[0].strip()}</div>
              <div style="margin-top:.4rem">
                <span class="badge b-blue">مصدر: {source}</span>
                <span class="badge {'b-green' if score>=60 else 'b-red' if score<40 else 'b-yellow'}" style="margin-right:.4rem">درجة: {score}/100</span>
                <span class="badge b-purple" style="margin-right:.4rem">ثقة: {confidence}%</span>
                <span class="badge b-orange" style="margin-right:.4rem">{trend_info['label']}</span>
              </div>
            </div>
            <div style="text-align:left">
              <div style="font-size:2.4rem;font-weight:900">{price:.3f} <span style="font-size:1rem;color:#8b949e">{currency}</span></div>
              <div style="color:{'#3fb950' if up else '#f85149'};font-size:1rem;font-weight:700">
                {'▲' if up else '▼'} {abs(change):.3f} ({chg_pct:+.2f}%)
              </div>
            </div>
          </div>
        </div>
        """,unsafe_allow_html=True)

        # ── ملخص سريع شامل ──────────────────────────────────
        rsi_v=safe(tech['rsi'].iloc[-1]); atr_v=safe(tech['atr'].iloc[-1])
        vol_v=df['Volume'].iloc[-1] if 'Volume' in df.columns else 0
        mc=info.get('marketCap',0)

        cols6=st.columns(6)
        mets=[
            ("الدرجة/الثقة",f"{score}/100 ({confidence}%)",'#3fb950' if score>=60 else '#f85149' if score<40 else '#d29922'),
            ("RSI(14)",f"{rsi_v:.1f}" if rsi_v else "—",'#3fb950' if rsi_v and rsi_v<30 else '#f85149' if rsi_v and rsi_v>70 else '#58a6ff'),
            ("الاتجاه",trend_info['label'].split()[0],trend_info['color']),
            ("التجميع",accum_info['phase'].split()[0],accum_info['color']),
            ("vs القطاع",sector_cmp['vs_label'][0].split()[0],sector_cmp['vs_label'][1]),
            ("سيولة ذكية","✅ مرتفعة" if accum_info['smart_money'] else "طبيعية",'#3fb950' if accum_info['smart_money'] else '#8b949e'),
        ]
        for col,(lbl,val,clr) in zip(cols6,mets):
            with col:
                st.markdown(f"""<div class="metric-card">
                  <div class="metric-val" style="color:{clr};font-size:1.1rem">{val}</div>
                  <div class="metric-lbl">{lbl}</div>
                </div>""",unsafe_allow_html=True)

        st.markdown("<br>",unsafe_allow_html=True)

        # ── التبويبات ────────────────────────────────────────
        tab_chart,tab_rec,tab_scenarios,tab_tech,tab_ai,tab_news,tab_info,tab_fib=st.tabs([
            "📈 الشارت","🎯 التوصية","🔮 السيناريوهات","📊 التحليل الفني",
            "🤖 تقرير AI","📰 الأخبار","ℹ️ معلومات","📐 فيبوناتشي"
        ])

        # ── TAB: الشارت ─────────────────────────────────────
        with tab_chart:
            # ملخص سريع أعلى الشارت
            sc1,sc2,sc3,sc4,sc5=st.columns(5)
            with sc1:
                st.markdown(f"""<div class="metric-card">
                  <div class="metric-val" style="color:{verdict[2]}">{verdict[0]}</div>
                  <div class="metric-lbl">التوصية</div>
                </div>""",unsafe_allow_html=True)
            with sc2:
                st.markdown(f"""<div class="metric-card">
                  <div class="metric-val" style="color:#3fb950">{targets['t1']:.3f}</div>
                  <div class="metric-lbl">🎯 هدف 1 (+{targets['dist_t1']}%)</div>
                </div>""",unsafe_allow_html=True)
            with sc3:
                st.markdown(f"""<div class="metric-card">
                  <div class="metric-val" style="color:#bc8cff">{targets['t2']:.3f}</div>
                  <div class="metric-lbl">🎯 هدف 2 (+{targets['dist_t2']}%)</div>
                </div>""",unsafe_allow_html=True)
            with sc4:
                st.markdown(f"""<div class="metric-card">
                  <div class="metric-val" style="color:#f85149">{targets['stop_loss']:.3f}</div>
                  <div class="metric-lbl">🛑 وقف الخسارة</div>
                </div>""",unsafe_allow_html=True)
            with sc5:
                st.markdown(f"""<div class="metric-card">
                  <div class="metric-val" style="color:#d29922">1:{targets['rr']}</div>
                  <div class="metric-lbl">⚖️ مخاطرة/عائد</div>
                </div>""",unsafe_allow_html=True)

            fig=build_chart(df,tech,symbol,targets,show_vol,candles)
            st.plotly_chart(fig,use_container_width=True,
                config={"displayModeBar":True,"displaylogo":False,"modeBarButtonsToRemove":["lasso2d","select2d"]})

            with st.expander("📖 دليل قراءة الشارت"):
                dc1,dc2,dc3=st.columns(3)
                with dc1:
                    st.markdown("""**خطوط على الشارت:**
- 🔴 خط أحمر صلب = مقاومة رئيسية
- 🟢 خط أخضر صلب = دعم رئيسي
- 🔵 خط أزرق متقطع = الهدف 1
- 🟣 خط أرجواني = الهدف 2
- 🔴 خط أحمر متقطع = وقف الخسارة""")
                with dc2:
                    st.markdown("""**علامات على الشارت:**
- ▲ مثلث أخضر = إشارة شراء
- ▼ مثلث أحمر = إشارة بيع
- منطقة خضراء = منطقة دخول مثالية
- BB أرجوانية = بولينجر باندز""")
                with dc3:
                    st.markdown("""**مؤشرات أسفل الشارت:**
- RSI > 70 = تشبع شرائي (تحذير)
- RSI < 30 = تشبع بيعي (فرصة)
- MACD أخضر = زخم صاعد
- الحجم = قوة الحركة""")

        # ── TAB: التوصية ────────────────────────────────────
        with tab_rec:
            st.markdown(f"""
            <div class="verdict-box {verdict[1]}">
              <div class="verdict-title" style="color:{verdict[2]}">{verdict[0]}</div>
              <div class="verdict-sub">درجة الثقة: {score}/100 | نسبة نجاح الإشارة: {confidence}% | مخاطرة/عائد: 1:{targets['rr']}</div>
            </div>
            """,unsafe_allow_html=True)

            # الأهداف مع المسافة والأيام
            c1,c2,c3,c4,c5=st.columns(5)
            tgt_items=[
                (c1,"سعر الدخول",f"{price:.3f}",'#58a6ff',""),
                (c2,"وقف الخسارة",f"{targets['stop_loss']:.3f}",'#f85149',f"{((targets['stop_loss']-price)/price*100):+.1f}%"),
                (c3,f"هدف 1 | ~{targets['days_t1']} يوم",f"{targets['t1']:.3f}",'#3fb950',f"+{targets['dist_t1']}%"),
                (c4,f"هدف 2 | ~{targets['days_t2']} يوم",f"{targets['t2']:.3f}",'#3fb950',f"+{targets['dist_t2']}%"),
                (c5,"هدف 3",f"{targets['t3']:.3f}",'#bc8cff',f"{((targets['t3']-price)/price*100):+.1f}%"),
            ]
            for col,lbl,val,clr,sub in tgt_items:
                with col:
                    st.markdown(f"""<div class="metric-card">
                      <div class="metric-val" style="color:{clr}">{val}</div>
                      <div class="metric-lbl">{lbl}</div>
                      <div style="color:{clr};font-size:.75rem">{sub}</div>
                    </div>""",unsafe_allow_html=True)

            # الإشارات
            st.markdown("<br>",unsafe_allow_html=True)
            st.markdown("### 📡 الإشارات التفصيلية")
            sig_cols=st.columns(len(signals))
            for i,(k,v) in enumerate(signals.items()):
                with sig_cols[i]:
                    st.markdown(f"""<div class="metric-card">
                      <div style="font-size:.75rem;color:#8b949e;margin-bottom:.3rem">{k}</div>
                      <span class="badge {v[1]}">{v[0]}</span>
                      <div style="font-size:.7rem;color:#8b949e;margin-top:.2rem">{'▲' if v[2]>0 else '▼' if v[2]<0 else '—'} {abs(v[2])}</div>
                    </div>""",unsafe_allow_html=True)

            # التجميع والسيولة الذكية
            st.markdown("<br>",unsafe_allow_html=True)
            st.markdown("### 💧 التجميع والسيولة الذكية")
            acc1,acc2,acc3,acc4=st.columns(4)
            with acc1:
                st.markdown(f"""<div class="metric-card">
                  <div class="metric-val" style="color:{accum_info['color']}">{accum_info['phase'].split()[0]}</div>
                  <div class="metric-lbl">مرحلة التجميع</div>
                </div>""",unsafe_allow_html=True)
            with acc2:
                st.markdown(f"""<div class="metric-card">
                  <div class="metric-val" style="color:#58a6ff">{accum_info['vol_ratio']}x</div>
                  <div class="metric-lbl">نسبة الحجم</div>
                </div>""",unsafe_allow_html=True)
            with acc3:
                sm_color='#3fb950' if accum_info['smart_money'] else '#8b949e'
                st.markdown(f"""<div class="metric-card">
                  <div class="metric-val" style="color:{sm_color}">{'✅ نعم' if accum_info['smart_money'] else '❌ لا'}</div>
                  <div class="metric-lbl">السيولة الذكية</div>
                </div>""",unsafe_allow_html=True)
            with acc4:
                st.markdown(f"""<div class="metric-card">
                  <div class="metric-val" style="color:{accum_info['color']}">{accum_info['score']}/100</div>
                  <div class="metric-lbl">درجة التجميع</div>
                </div>""",unsafe_allow_html=True)

            # مقارنة القطاع
            st.markdown("<br>",unsafe_allow_html=True)
            st.markdown("### 📊 مقارنة مع القطاع")
            sq1,sq2,sq3,sq4=st.columns(4)
            with sq1:
                st.markdown(f"""<div class="metric-card">
                  <div class="metric-val" style="color:#8b949e">{sector_cmp['sector'][:12]}</div>
                  <div class="metric-lbl">القطاع</div>
                </div>""",unsafe_allow_html=True)
            with sq2:
                vs_c=sector_cmp['vs_label'][1]
                st.markdown(f"""<div class="metric-card">
                  <div class="metric-val" style="color:{vs_c}">{sector_cmp['vs_sector']:+.0f}</div>
                  <div class="metric-lbl">فرق الدرجة (متوسط القطاع: {sector_cmp['sector_score']})</div>
                </div>""",unsafe_allow_html=True)
            with sq3:
                pe_c='#3fb950' if sector_cmp.get('pe_vs_sector') and sector_cmp['pe_vs_sector']<0 else '#f85149'
                st.markdown(f"""<div class="metric-card">
                  <div class="metric-val" style="color:{pe_c}">{f"{sector_cmp['pe_vs_sector']:+.1f}%" if sector_cmp.get('pe_vs_sector') else "—"}</div>
                  <div class="metric-lbl">P/E vs القطاع ({sector_cmp['sector_pe']}x)</div>
                </div>""",unsafe_allow_html=True)
            with sq4:
                st.markdown(f"""<div class="metric-card">
                  <div class="metric-val" style="color:{sector_cmp['vs_label'][1]};font-size:.9rem">{sector_cmp['vs_label'][0]}</div>
                  <div class="metric-lbl">تقييم نسبي</div>
                </div>""",unsafe_allow_html=True)

            # السعر العادل
            st.markdown("<br>",unsafe_allow_html=True)
            st.markdown("### 💰 السعر العادل والتقييم")
            fv1,fv2,fv3,fv4=st.columns(4)
            with fv1:
                g=fair_val.get('graham')
                st.markdown(f"""<div class="metric-card">
                  <div class="metric-val" style="color:#bc8cff">{f"{g:.3f}" if g else "—"}</div>
                  <div class="metric-lbl">Graham Number</div>
                </div>""",unsafe_allow_html=True)
            with fv2:
                fp=fair_val.get('fair_pe')
                st.markdown(f"""<div class="metric-card">
                  <div class="metric-val" style="color:#58a6ff">{f"{fp:.3f}" if fp else "—"}</div>
                  <div class="metric-lbl">P/E العادل</div>
                </div>""",unsafe_allow_html=True)
            with fv3:
                af=fair_val.get('avg_fair')
                st.markdown(f"""<div class="metric-card">
                  <div class="metric-val" style="color:#d29922">{f"{af:.3f}" if af else "—"}</div>
                  <div class="metric-lbl">متوسط السعر العادل</div>
                </div>""",unsafe_allow_html=True)
            with fv4:
                vt=fair_val.get('valuation')
                if vt:
                    st.markdown(f"""<div class="metric-card">
                      <div class="metric-val" style="color:{vt[1]};font-size:.9rem">{vt[0]}</div>
                      <div class="metric-lbl">هامش أمان: {vt[2]:+.1f}%</div>
                    </div>""",unsafe_allow_html=True)

            # مناطق الدخول والخروج
            st.markdown("<br>",unsafe_allow_html=True)
            st.markdown("### 🎯 مناطق الدخول والخروج")
            ez1,ez2=st.columns(2)
            with ez1:
                st.markdown("**🟢 مناطق الشراء**")
                for z in fair_val.get('entry_zones',[]):
                    st.markdown(f"""<div style="background:rgba(63,185,80,0.1);border:1px solid #3fb950;border-radius:8px;padding:.7rem;margin-bottom:.5rem">
                      <div style="color:#3fb950;font-weight:700">{z['zone']}</div>
                      <div>من <strong>{z['from']:.3f}</strong> إلى <strong>{z['to']:.3f}</strong></div>
                      <div style="color:#8b949e;font-size:.8rem">{z['type']}</div>
                    </div>""",unsafe_allow_html=True)
            with ez2:
                st.markdown("**🔴 مناطق الخروج/البيع**")
                for z in fair_val.get('sell_zones',[]):
                    st.markdown(f"""<div style="background:rgba(248,81,73,0.1);border:1px solid #f85149;border-radius:8px;padding:.7rem;margin-bottom:.5rem">
                      <div style="color:#f85149;font-weight:700">{z['zone']}</div>
                      <div>من <strong>{z['from']:.3f}</strong> إلى <strong>{z['to']:.3f}</strong></div>
                      <div style="color:#8b949e;font-size:.8rem">{z['type']}</div>
                    </div>""",unsafe_allow_html=True)

            # الشموع اليابانية
            st.markdown("<br>",unsafe_allow_html=True)
            st.markdown("### 🕯️ نماذج الشموع اليابانية")
            if candles:
                cc=st.columns(min(len(candles),3))
                for i,c in enumerate(candles[:3]):
                    bull=c.get('bullish')
                    clr='#3fb950' if bull else '#f85149' if bull is False else '#d29922'
                    icon='↑' if bull else '↓' if bull is False else '↔'
                    with cc[i%3]:
                        st.markdown(f"""<div class="metric-card" style="border-color:{clr}">
                          <div style="font-size:1.1rem;font-weight:700;color:{clr}">{icon} {c['name']}</div>
                          <div style="color:#8b949e;font-size:.78rem;margin:.3rem 0">{c['type']}</div>
                          <span class="badge" style="background:rgba(0,0,0,.3);color:{clr};border:1px solid {clr}">{c['signal']}</span>
                          <div style="color:#8b949e;font-size:.72rem;margin-top:.3rem">قوة: {c['strength']}</div>
                        </div>""",unsafe_allow_html=True)

            # الدعم والمقاومة مع التنبيهات
            st.markdown("<br>",unsafe_allow_html=True)
            st.markdown("### 📍 الدعم والمقاومة")
            sr1,sr2=st.columns(2)
            with sr1:
                st.markdown("**🔴 المقاومة**")
                for r in tech['resistance']:
                    diff=(r-price)/price*100
                    days=max(3,int(abs(diff)/0.3))
                    st.markdown(f"`{r:.3f}` ({diff:+.1f}%) — ~{days} جلسة")
            with sr2:
                st.markdown("**🟢 الدعم**")
                for s in tech['support']:
                    diff=(s-price)/price*100
                    st.markdown(f"`{s:.3f}` ({diff:+.1f}%) {'⚠️ قريب!' if abs(diff)<2 else ''}")

            if st.button(f"➕ إضافة {symbol} للمراقبة",use_container_width=True):
                entry=(symbol,market)
                if entry not in st.session_state.get('watchlist',[]):
                    if 'watchlist' not in st.session_state: st.session_state.watchlist=[]
                    st.session_state.watchlist.append(entry)
                    st.success(f"✅ تمت إضافة {symbol}")

        # ── TAB: السيناريوهات ────────────────────────────────
        with tab_scenarios:
            st.markdown("### 🔮 السيناريوهات والتوقعات")

            # السيناريو الإيجابي والسلبي
            sc_pos,sc_neg=st.columns(2)
            with sc_pos:
                pos=scenarios['positive']
                st.markdown(f"""<div style="background:rgba(63,185,80,0.1);border:2px solid #3fb950;border-radius:12px;padding:1.2rem">
                  <div style="font-size:1.1rem;font-weight:700;color:#3fb950;margin-bottom:.8rem">{pos['label']}</div>
                  <div style="margin-bottom:.4rem">احتمالية: <strong style="color:#3fb950">{pos['prob']}%</strong></div>
                  <div>الهدف الأول: <strong>{pos['t1']:.3f}</strong> ({(pos['t1']-price)/price*100:+.1f}%)</div>
                  <div>الهدف الثاني: <strong>{pos['t2']:.3f}</strong> ({(pos['t2']-price)/price*100:+.1f}%)</div>
                  <div style="color:#8b949e;font-size:.85rem;margin-top:.5rem">
                    يتحقق عند كسر {scenarios['nearest_res']:.3f} بحجم قوي
                  </div>
                </div>""",unsafe_allow_html=True)
            with sc_neg:
                neg=scenarios['negative']
                st.markdown(f"""<div style="background:rgba(248,81,73,0.1);border:2px solid #f85149;border-radius:12px;padding:1.2rem">
                  <div style="font-size:1.1rem;font-weight:700;color:#f85149;margin-bottom:.8rem">{neg['label']}</div>
                  <div style="margin-bottom:.4rem">احتمالية: <strong style="color:#f85149">{neg['prob']}%</strong></div>
                  <div>الدعم الأول: <strong>{neg['t1']:.3f}</strong> ({(neg['t1']-price)/price*100:+.1f}%)</div>
                  <div>الدعم الثاني: <strong>{neg['t2']:.3f}</strong> ({(neg['t2']-price)/price*100:+.1f}%)</div>
                  <div style="color:#8b949e;font-size:.85rem;margin-top:.5rem">
                    يتحقق عند كسر {scenarios['nearest_sup']:.3f} إلى الأسفل
                  </div>
                </div>""",unsafe_allow_html=True)

            # النطاق الأسبوعي
            st.markdown("<br>",unsafe_allow_html=True)
            st.markdown("### 📊 النطاق السعري المتوقع")
            nr1,nr2,nr3,nr4=st.columns(4)
            with nr1:
                st.markdown(f"""<div class="metric-card" style="border-color:#3fb950">
                  <div class="metric-val" style="color:#3fb950">{scenarios['weekly_range']['high']:.3f}</div>
                  <div class="metric-lbl">أعلى نطاق أسبوعي</div>
                </div>""",unsafe_allow_html=True)
            with nr2:
                st.markdown(f"""<div class="metric-card" style="border-color:#f85149">
                  <div class="metric-val" style="color:#f85149">{scenarios['weekly_range']['low']:.3f}</div>
                  <div class="metric-lbl">أدنى نطاق أسبوعي</div>
                </div>""",unsafe_allow_html=True)
            with nr3:
                st.markdown(f"""<div class="metric-card" style="border-color:#f85149">
                  <div class="metric-val" style="color:#f85149">{scenarios['nearest_res']:.3f}</div>
                  <div class="metric-lbl">أقرب مقاومة</div>
                </div>""",unsafe_allow_html=True)
            with nr4:
                st.markdown(f"""<div class="metric-card" style="border-color:#3fb950">
                  <div class="metric-val" style="color:#3fb950">{scenarios['nearest_sup']:.3f}</div>
                  <div class="metric-lbl">أقرب دعم</div>
                </div>""",unsafe_allow_html=True)

            # التوقعات السعرية
            st.markdown("<br>",unsafe_allow_html=True)
            st.markdown("### 📈 التوقعات السعرية التفصيلية")
            st.markdown("**أهداف الصعود:**")
            for t in targets_up:
                prob_c='#3fb950' if t['probability']>=65 else '#d29922' if t['probability']>=50 else '#8b949e'
                dist_pct=round((t['price']-price)/price*100,1)
                st.markdown(f"""<div class="target-row" style="background:#161b22;border:1px solid #30363d">
                  <span style="color:#8b949e">{t['type']}</span>
                  <span style="font-weight:700;color:#3fb950">{t['price']:.3f}</span>
                  <span style="color:#3fb950">{dist_pct:+.1f}%</span>
                  <span style="color:{prob_c}">احتمالية: {t['probability']}%</span>
                  <span style="color:#8b949e">~{t['days']} يوم</span>
                </div>""",unsafe_allow_html=True)

            if targets_down:
                st.markdown("**مستويات الدعم/وقف الخسارة:**")
                for t in targets_down:
                    dist_pct=round((t['price']-price)/price*100,1)
                    st.markdown(f"""<div class="target-row" style="background:#161b22;border:1px solid #30363d">
                      <span style="color:#8b949e">{t['type']}</span>
                      <span style="font-weight:700;color:#f85149">{t['price']:.3f}</span>
                      <span style="color:#f85149">{dist_pct:+.1f}%</span>
                    </div>""",unsafe_allow_html=True)

        # ── TAB: التحليل الفني ───────────────────────────────
        with tab_tech:
            c1,c2=st.columns(2)
            with c1:
                st.markdown("**المؤشرات الفنية**")
                for lbl,key in [("RSI(14)","rsi"),("MACD","macd"),("MACD Signal","macd_sig"),("MACD Hist","macd_hist"),("Stoch K","stoch_k"),("Stoch D","stoch_d")]:
                    v=safe(tech[key].iloc[-1])
                    v_str = f"{v:.4f}" if v is not None else "—"
                    st.markdown(f"**{lbl}:** `{v_str}`")
            with c2:
                st.markdown("**المتوسطات المتحركة**")
                for lbl,key in [("EMA9","ema9"),("SMA20","sma20"),("SMA50","sma50"),("SMA200","sma200"),("BB Upper","bb_upper"),("BB Lower","bb_lower"),("ATR(14)","atr")]:
                    v=safe(tech[key].iloc[-1])
                    clr="#3fb950" if v and price>v else "#f85149" if v and price<v else "#8b949e"
                    v_str=f"{v:.3f}" if v is not None else "—"
                    st.markdown(f"**{lbl}:** <span style='color:{clr}'>`{v_str}`</span>",unsafe_allow_html=True)

            # الاتجاه التفصيلي
            st.markdown("### 📊 تحليل الاتجاه")
            t1c,t2c,t3c=st.columns(3)
            with t1c:
                st.markdown(f"""<div class="metric-card">
                  <div class="metric-val" style="color:{trend_info['color']}">{trend_info['label']}</div>
                  <div class="metric-lbl">الاتجاه العام</div>
                </div>""",unsafe_allow_html=True)
            with t2c:
                slope_c='#3fb950' if trend_info['slope_20']>0 else '#f85149'
                st.markdown(f"""<div class="metric-card">
                  <div class="metric-val" style="color:{slope_c}">{trend_info['slope_20']:+.1f}%</div>
                  <div class="metric-lbl">تغير 20 يوم</div>
                </div>""",unsafe_allow_html=True)
            with t3c:
                slope_c='#3fb950' if trend_info['slope_50']>0 else '#f85149'
                st.markdown(f"""<div class="metric-card">
                  <div class="metric-val" style="color:{slope_c}">{trend_info['slope_50']:+.1f}%</div>
                  <div class="metric-lbl">تغير 50 يوم</div>
                </div>""",unsafe_allow_html=True)

        # ── TAB: تقرير AI ────────────────────────────────────
        with tab_ai:
            st.markdown("### 🤖 تقرير الذكاء الاصطناعي")
            if not api_key:
                st.info("💡 أضف مفتاح Claude AI في الشريط الجانبي للحصول على تقرير احترافي أكثر تفصيلاً.")
            with st.spinner("🤖 جاري توليد التقرير..."):
                ai_report=generate_ai_analysis(symbol,price,currency,score,verdict[0],signals,tech,info,news_sent,api_key)
            st.markdown(f'<div class="ai-box">{ai_report}</div>',unsafe_allow_html=True)

        # ── TAB: الأخبار ─────────────────────────────────────
        with tab_news:
            st.markdown(f"""### 📰 تحليل الأخبار
**المشاعر:** `{news_sent['sentiment']}` | الدرجة: **{news_sent['score']}/100**
| إيجابي: {news_sent['pos']} | سلبي: {news_sent['neg']} | محايد: {news_sent['neu']}""")
            if news_sent['items']:
                for item in news_sent['items']:
                    clr='#3fb950' if item['sentiment']=='إيجابي' else '#f85149' if item['sentiment']=='سلبي' else '#8b949e'
                    st.markdown(f"""<div class="news-item">
                      <span class="badge" style="background:rgba(0,0,0,.3);color:{clr};border:1px solid {clr}">{item['sentiment']}</span>
                      <strong style="margin-right:.4rem">{item.get('title','')}</strong>
                      <div style="color:#8b949e;font-size:.78rem;margin-top:.3rem">{item.get('date','')}</div>
                    </div>""",unsafe_allow_html=True)
            else:
                st.info("لا تتوفر أخبار حالياً.")

        # ── TAB: معلومات ─────────────────────────────────────
        with tab_info:
            if info:
                st.markdown("### ℹ️ معلومات الشركة")
                fields=[("الاسم الكامل",info.get('longName','—')),("القطاع",info.get('sector','—')),
                    ("الصناعة",info.get('industry','—')),("البورصة",info.get('exchange','—')),
                    ("العملة",info.get('currency','—')),("الدولة",info.get('country','—')),
                    ("الموظفون",f"{info.get('fullTimeEmployees',0):,}" if info.get('fullTimeEmployees') else '—'),
                    ("القيمة السوقية",f"{info.get('marketCap',0)/1e9:.2f}B" if info.get('marketCap') else '—'),
                    ("P/E الحالي",f"{info.get('trailingPE','—'):.2f}" if isinstance(info.get('trailingPE'),float) else '—'),
                    ("P/E المستقبلي",f"{info.get('forwardPE','—'):.2f}" if isinstance(info.get('forwardPE'),float) else '—'),
                    ("EPS",f"{info.get('trailingEps','—'):.3f}" if isinstance(info.get('trailingEps'),float) else '—'),
                    ("هامش الربح",f"{info.get('profitMargins',0)*100:.1f}%" if info.get('profitMargins') else '—'),
                    ("عائد التوزيعات",f"{info.get('dividendYield',0)*100:.2f}%" if info.get('dividendYield') else '—'),
                    ("أعلى 52 أسبوع",f"{info.get('fiftyTwoWeekHigh','—'):.3f}" if isinstance(info.get('fiftyTwoWeekHigh'),float) else '—'),
                    ("أدنى 52 أسبوع",f"{info.get('fiftyTwoWeekLow','—'):.3f}" if isinstance(info.get('fiftyTwoWeekLow'),float) else '—')]
                c1,c2=st.columns(2)
                for i,(lbl,val) in enumerate(fields):
                    with (c1 if i%2==0 else c2): st.markdown(f"**{lbl}:** `{val}`")
                desc=info.get('longBusinessSummary','')
                if desc:
                    with st.expander("📝 نبذة عن الشركة"): st.write(desc[:800])
            else:
                st.info("المعلومات التفصيلية غير متاحة. جرب سهماً أمريكياً.")

        # ── TAB: فيبوناتشي ───────────────────────────────────
        with tab_fib:
            st.markdown("### 📐 مستويات فيبوناتشي — ارتداد وامتداد")
            fibs=tech['fibs']; curr_p=price
            st.markdown("> **الارتداد:** 38.2% و50% و61.8% مناطق شراء محتملة | **الامتداد:** 127.2% و161.8% أهداف صعود")

            fib_zones={
                "0%":("مقاومة رئيسية — بيع/جني أرباح","#f85149","بيع"),
                "23.6%":("دعم خفيف — مراقبة","#f0883e","مراقبة"),
                "38.2%":("ارتداد متوسط — شراء محتمل ⭐","#d29922","شراء محتمل"),
                "50%":("ارتداد قوي — شراء جيد ⭐⭐","#58a6ff","شراء"),
                "61.8%":("الذهبي — شراء ممتاز ⭐⭐⭐","#3fb950","شراء ممتاز"),
                "78.6%":("ارتداد عميق — دعم قوي","#bc8cff","شراء مخاطرة"),
                "100%":("قاع الموجة","#6b7280","انتظار"),
                "127.2%":("امتداد 1 — هدف صعود 🎯","#3fb950","هدف 1"),
                "161.8%":("امتداد ذهبي — هدف رئيسي 🎯🎯","#bc8cff","هدف 2"),
            }
            for level,val in fibs.items():
                if val is None: continue
                diff=(val-curr_p)/curr_p*100
                zone_desc,zone_color,zone_type=fib_zones.get(level,("—","#8b949e","—"))
                is_current=abs(diff)<2
                border=f"border:2px solid {zone_color}" if is_current else "border:1px solid #30363d"
                bg=f"background:rgba(88,166,255,0.1)" if is_current else "background:#161b22"
                current_badge='<span style="background:#58a6ff;color:#000;border-radius:4px;padding:1px 6px;font-size:.7rem;margin-right:.3rem">الحالي</span>' if is_current else ""
                st.markdown(f"""<div style="display:flex;justify-content:space-between;align-items:center;
                     padding:.7rem 1rem;{bg};border-radius:10px;margin-bottom:.4rem;{border}">
                  <div style="min-width:80px"><span style="color:#8b949e;font-size:.85rem">Fib {level}</span>{current_badge}</div>
                  <div style="flex:1;text-align:center"><span style="color:#8b949e;font-size:.8rem">{zone_desc}</span></div>
                  <div style="text-align:right;min-width:150px">
                    <span style="color:{zone_color};font-weight:700">{val:.3f}</span>
                    <span style="color:{zone_color};font-size:.85rem;margin-right:.5rem"> ({diff:+.1f}%)</span>
                    <span class="badge" style="background:rgba(0,0,0,.3);color:{zone_color};border:1px solid {zone_color}">{zone_type}</span>
                  </div>
                </div>""",unsafe_allow_html=True)

            # ملخص فيبوناتشي
            cs=None; cr=None
            for lv,vl in fibs.items():
                if vl and vl<curr_p and (cs is None or vl>cs): cs=vl
                if vl and vl>curr_p and (cr is None or vl<cr): cr=vl
            if cs or cr:
                st.markdown(f"""<div class="ai-box" style="margin-top:.8rem">
                  <strong>📊 ملخص فيبوناتشي:</strong><br>
                  {'أقرب دعم: <strong style="color:#3fb950">' + f"{cs:.3f}" + f'</strong> ({(cs-curr_p)/curr_p*100:+.1f}%)' if cs else ""}
                  {'&nbsp;&nbsp;|&nbsp;&nbsp;' if cs and cr else ""}
                  {'أقرب مقاومة: <strong style="color:#f85149">' + f"{cr:.3f}" + f'</strong> ({(cr-curr_p)/curr_p*100:+.1f}%)' if cr else ""}
                  <br>
                  {'<span style="color:#d29922">📍 السعر الحالي قريب من مستوى فيبوناتشي — انتبه للارتداد!</span>' if min(abs((cs-curr_p)/curr_p*100) if cs else 99, abs((cr-curr_p)/curr_p*100) if cr else 99) < 2 else ""}
                </div>""",unsafe_allow_html=True)

        # حفظ السجل
        if 'history' not in st.session_state: st.session_state.history=[]
        st.session_state.history.append({"time":datetime.now().strftime("%H:%M:%S"),
            "symbol":symbol,"price":price,"score":score,"verdict":verdict[0],
            "market":market_label.split('(')[0].strip(),"confidence":confidence})
        if len(st.session_state.history)>20:
            st.session_state.history=st.session_state.history[-20:]

# ── باقي الصفحات ──────────────────────────────────────
elif nav=="⚖️ مقارنة":
    st.markdown("### ⚖️ مقارنة سهمين")
    c1,c2=st.columns(2)
    with c1: sym1=st.text_input("السهم الأول","2222").strip().upper(); mkt1=st.selectbox("السوق 1",list(MARKETS.keys()),key="m1")
    with c2: sym2=st.text_input("السهم الثاني","1120").strip().upper(); mkt2=st.selectbox("السوق 2",list(MARKETS.keys()),key="m2")
    if st.button("⚖️ مقارنة الآن",use_container_width=True):
        with st.spinner("جاري التحليل..."):
            d1=get_stock_data(sym1,MARKETS[mkt1]); d2=get_stock_data(sym2,MARKETS[mkt2])
        for sym,data,mkt in [(sym1,d1,mkt1),(sym2,d2,mkt2)]:
            if data['error']: st.error(f"❌ {sym}: {data['error']}"); continue
            tech_t=analyze_technicals(data['hist'])
            _,sc_t,vd_t,tg_t=generate_signals(data['hist'],tech_t)
            tr_t=detect_trend(data['hist'],tech_t)
            ac_t=detect_accumulation_distribution(data['hist'],tech_t)
            pr_t=data['price'] or float(data['hist']['Close'].iloc[-1])
            st.markdown(f"""<div class="card">
              <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap">
                <div><h3>{sym}</h3><div style="color:#8b949e">{mkt.split('(')[0].strip()}</div></div>
                <div style="text-align:left">
                  <div style="font-size:1.5rem;font-weight:900">{pr_t:.3f}</div>
                  <div style="color:{'#3fb950' if 'شراء' in vd_t[0] else '#f85149'}">{vd_t[0]}</div>
                </div>
              </div>
              <div style="margin-top:.5rem">
                درجة: <strong>{sc_t}/100</strong> | اتجاه: <strong style="color:{tr_t['color']}">{tr_t['label']}</strong> |
                تجميع: <strong style="color:{ac_t['color']}">{ac_t['phase']}</strong> |
                هدف 1: <strong>{tg_t['t1']:.3f}</strong> | وقف: <strong style="color:#f85149">{tg_t['stop_loss']:.3f}</strong>
              </div>
            </div>""",unsafe_allow_html=True)

elif nav=="💼 المحفظة":
    st.markdown("### 💼 المحفظة الاستثمارية")
    if 'portfolio' not in st.session_state: st.session_state.portfolio=[]
    with st.form("add_portfolio"):
        pc1,pc2,pc3,pc4=st.columns(4)
        with pc1: p_sym=st.text_input("رمز السهم").strip().upper()
        with pc2: p_mkt=st.selectbox("السوق",list(MARKETS.keys()),key="pmkt")
        with pc3: p_qty=st.number_input("الكمية",min_value=1,value=100)
        with pc4: p_cost=st.number_input("متوسط التكلفة",min_value=0.0,value=0.0,step=0.01)
        if st.form_submit_button("➕ إضافة"):
            if p_sym:
                st.session_state.portfolio.append({"symbol":p_sym,"market":MARKETS[p_mkt],"qty":p_qty,"cost":p_cost,"added":datetime.now().strftime("%Y-%m-%d")})
                st.success(f"✅ تمت إضافة {p_sym}")
    if st.session_state.portfolio:
        st.markdown("---")
        total_value=total_cost=0
        for i,pos in enumerate(st.session_state.portfolio):
            dp=get_stock_data(pos['symbol'],pos['market'])
            if not dp['error']:
                cp=dp['price'] or float(dp['hist']['Close'].iloc[-1])
                value=cp*pos['qty']; cost_t=pos['cost']*pos['qty']
                pnl=value-cost_t; pnl_pct=(pnl/cost_t*100) if cost_t else 0
                total_value+=value; total_cost+=cost_t
                color='#3fb950' if pnl>=0 else '#f85149'
                # تحليل سريع للمحفظة
                tech_p=analyze_technicals(dp['hist'])
                _,sc_p,vd_p,_=generate_signals(dp['hist'],tech_p)
                tr_p=detect_trend(dp['hist'],tech_p)
                st.markdown(f"""<div class="portfolio-card">
                  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:.5rem">
                    <div>
                      <strong style="font-size:1.1rem">{pos['symbol']}</strong>
                      <span style="color:#8b949e;margin-right:.5rem"> {pos['qty']} وحدة @ {pos['cost']:.3f}</span>
                      <span class="badge {'b-green' if sc_p>=60 else 'b-red' if sc_p<40 else 'b-yellow'}">{vd_p[0]}</span>
                      <span style="color:{tr_p['color']};font-size:.8rem;margin-right:.3rem"> {tr_p['label'].split()[0]}</span>
                    </div>
                    <div style="text-align:left">
                      <div>القيمة: <strong>{value:,.2f}</strong></div>
                      <div style="color:{color}">ر/خ: {pnl:+,.2f} ({pnl_pct:+.1f}%)</div>
                    </div>
                  </div>
                </div>""",unsafe_allow_html=True)
            if st.button(f"🗑️ حذف {pos['symbol']}",key=f"del_{i}"):
                st.session_state.portfolio.pop(i); st.rerun()
        if total_cost>0:
            total_pnl=total_value-total_cost; total_pct=total_pnl/total_cost*100
            color_t='#3fb950' if total_pnl>=0 else '#f85149'
            st.markdown(f"""<div class="card" style="border-color:#58a6ff;margin-top:1rem">
              <h3>📊 ملخص المحفظة</h3>
              <p>القيمة: <strong>{total_value:,.2f}</strong> | ر/خ: <strong style="color:{color_t}">{total_pnl:+,.2f} ({total_pct:+.1f}%)</strong></p>
            </div>""",unsafe_allow_html=True)
    else: st.info("💡 أضف أسهمك للمتابعة.")

elif nav=="🔔 التنبيهات":
    st.markdown("### 🔔 تنبيهات الأسعار")
    if 'alerts' not in st.session_state: st.session_state.alerts=[]
    with st.form("add_alert"):
        ac1,ac2,ac3,ac4=st.columns(4)
        with ac1: a_sym=st.text_input("رمز السهم").strip().upper()
        with ac2: a_mkt=st.selectbox("السوق",list(MARKETS.keys()),key="amkt")
        with ac3: a_type=st.selectbox("نوع التنبيه",["أعلى من","أقل من","كسر مقاومة","كسر دعم"])
        with ac4: a_price=st.number_input("السعر المستهدف",min_value=0.0,step=0.01)
        if st.form_submit_button("➕ إضافة تنبيه"):
            if a_sym and a_price>0:
                st.session_state.alerts.append({"symbol":a_sym,"market":MARKETS[a_mkt],"type":a_type,"price":a_price,"created":datetime.now().strftime("%Y-%m-%d %H:%M")})
                st.success(f"✅ تم: {a_sym} {a_type} {a_price}")
    if st.session_state.alerts:
        st.markdown("---")
        for i,alert in enumerate(st.session_state.alerts):
            da=get_stock_data(alert['symbol'],alert['market'])
            if not da['error']:
                ca=da['price'] or float(da['hist']['Close'].iloc[-1])
                triggered=(alert['type']=="أعلى من" and ca>=alert['price']) or (alert['type']=="أقل من" and ca<=alert['price'])
                border='#3fb950' if triggered else '#30363d'
                status="🔔 مُفعَّل!" if triggered else "⏳ منتظر"
                diff_pct=(ca-alert['price'])/alert['price']*100
                st.markdown(f"""<div class="alert-card" style="border-color:{border}">
                  <div style="display:flex;justify-content:space-between">
                    <div><strong>{alert['symbol']}</strong> | {alert['type']} {alert['price']:.3f}</div>
                    <div>الحالي: {ca:.3f} ({diff_pct:+.1f}%) | {status}</div>
                  </div>
                </div>""",unsafe_allow_html=True)
            if st.button(f"🗑️ حذف {i+1}",key=f"del_a_{i}"):
                st.session_state.alerts.pop(i); st.rerun()
    else: st.info("💡 أضف تنبيهات لمتابعة أسعار الأسهم.")

elif nav=="👁️ المراقبة":
    st.markdown("### 👁️ قائمة المراقبة")
    if 'watchlist' not in st.session_state:
        st.session_state.watchlist=[("2222","sa"),("1120","sa"),("AAPL","us"),("NVDA","us")]
    if st.button("🔄 تحديث الكل"): st.rerun()
    for sym,mkt in st.session_state.watchlist:
        dw=get_stock_data(sym,mkt)
        if not dw['error']:
            tw=analyze_technicals(dw['hist'])
            _,sw,vw,tgw=generate_signals(dw['hist'],tw)
            trw=detect_trend(dw['hist'],tw)
            acw=detect_accumulation_distribution(dw['hist'],tw)
            pw=dw['price'] or float(dw['hist']['Close'].iloc[-1])
            prev_w=float(dw['hist']['Close'].iloc[-2]) if len(dw['hist'])>1 else pw
            chg_w=pw-prev_w; chg_p_w=(chg_w/prev_w*100) if prev_w else 0
            color_w='#3fb950' if chg_w>=0 else '#f85149'
            st.markdown(f"""<div class="card" style="margin-bottom:.5rem">
              <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:.5rem">
                <div>
                  <strong style="font-size:1.1rem">{sym}</strong>
                  <span class="badge {'b-green' if sw>=60 else 'b-red' if sw<40 else 'b-yellow'}" style="margin-right:.4rem">{vw[0]}</span>
                  <span style="color:{trw['color']};font-size:.8rem">{trw['label'].split()[0]}</span>
                  <span style="color:{acw['color']};font-size:.8rem;margin-right:.3rem"> | {acw['phase'].split()[0]}</span>
                </div>
                <div style="text-align:left">
                  <strong>{pw:.3f}</strong> <span style="color:{color_w}">({chg_p_w:+.1f}%)</span>
                  <div style="font-size:.8rem;color:#8b949e">هدف: {tgw['t1']:.3f} | وقف: {tgw['stop_loss']:.3f}</div>
                </div>
              </div>
            </div>""",unsafe_allow_html=True)
    if not st.session_state.watchlist: st.info("أضف أسهماً من صفحة التحليل.")

elif nav=="📜 السجل":
    st.markdown("### 📜 سجل التحليلات")
    history=st.session_state.get('history',[])
    if history:
        for h in reversed(history[-20:]):
            color='#3fb950' if 'شراء' in h['verdict'] else '#f85149' if 'بيع' in h['verdict'] else '#d29922'
            st.markdown(f"""<div class="card" style="margin-bottom:.4rem">
              <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:.5rem">
                <span><strong>{h['symbol']}</strong> | {h['market']}</span>
                <span>{h['price']:.3f} | درجة: {h['score']}/100 | ثقة: {h.get('confidence','-')}% | <strong style="color:{color}">{h['verdict']}</strong></span>
                <span style="color:#8b949e;font-size:.8rem">{h['time']}</span>
              </div>
            </div>""",unsafe_allow_html=True)
        if st.button("🗑️ مسح السجل"): st.session_state.history=[]; st.rerun()
    else: st.info("لا يوجد سجل بعد.")
