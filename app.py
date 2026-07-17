import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import warnings, io, json, time, requests
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
.metric-card{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:.9rem;text-align:center;}
.metric-val{font-size:1.45rem;font-weight:900;}
.metric-lbl{color:#8b949e;font-size:.75rem;margin-top:.15rem;}
.news-item{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:.85rem;margin-bottom:.5rem;}
.progress-bar{height:8px;border-radius:4px;background:#21262d;overflow:hidden;margin:.3rem 0;}
.progress-fill{height:100%;border-radius:4px;}
.stTabs [data-baseweb="tab"]{font-family:'Cairo',sans-serif;font-size:.88rem;}
.stButton>button{border-radius:10px;font-family:'Cairo',sans-serif;font-weight:700;}
.ai-box{background:linear-gradient(135deg,#161b22,#0d1117);border:1px solid #58a6ff;border-radius:12px;padding:1.2rem;margin:.8rem 0;}
.portfolio-card{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:1rem;margin-bottom:.6rem;}
.alert-card{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:.9rem;margin-bottom:.5rem;}
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════
# مصدر البيانات: Stooq + yfinance
# ═══════════════════════════════════════════════════════

def to_stooq_symbol(symbol: str, market: str) -> str:
    s = symbol.upper().strip()
    if market in ("sa", "saudi", "tasi"):
        return f"{s.lower()}.sr"
    elif market == "us":
        return f"{s.lower()}.us"
    elif market == "ae":
        return f"{s.lower()}.ae"
    elif market == "gb":
        return f"{s.lower()}.uk"
    elif market == "de":
        return f"{s.lower()}.de"
    else:
        return f"{s.lower()}.us"

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
        if 'date' not in df.columns:
            return pd.DataFrame()
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').tail(365)
        col_map = {"open":"Open","high":"High","low":"Low","close":"Close","volume":"Volume"}
        df = df.rename(columns=col_map)
        df.index = df['date']
        cols = [c for c in ['Open','High','Low','Close','Volume'] if c in df.columns]
        return df[cols].dropna(subset=['Close'])
    except Exception:
        return pd.DataFrame()

def fetch_yfinance_data(symbol: str, market: str):
    try:
        import yfinance as yf
        if market in ("sa","saudi","tasi"):
            yf_sym = f"{symbol}.SR"
        else:
            yf_sym = symbol.upper()
        ticker = yf.Ticker(yf_sym)
        hist = ticker.history(period="1y")
        info = {}
        try:
            info = ticker.info or {}
        except Exception:
            pass
        news = []
        try:
            raw_news = ticker.news or []
            for n in raw_news[:8]:
                news.append({
                    "title": n.get("title",""),
                    "link":  n.get("link",""),
                    "date":  datetime.fromtimestamp(n.get("providerPublishTime",0)).strftime("%Y-%m-%d") if n.get("providerPublishTime") else ""
                })
        except Exception:
            pass
        return hist, info, news
    except Exception:
        return pd.DataFrame(), {}, []

def get_stock_data(symbol: str, market: str) -> dict:
    result = {"hist": pd.DataFrame(), "info": {}, "news": [], "price": None, "source": "none", "error": None}

    # Stooq أولاً
    hist_stooq = fetch_stooq(symbol, market)
    if not hist_stooq.empty and len(hist_stooq) >= 10:
        result["hist"] = hist_stooq
        result["price"] = float(hist_stooq['Close'].iloc[-1])
        result["source"] = "stooq"

    # yfinance للمعلومات الإضافية والأخبار
    try:
        hist_yf, info_yf, news_yf = fetch_yfinance_data(symbol, market)
        if not hist_yf.empty and result["hist"].empty:
            result["hist"] = hist_yf
            result["source"] = "yfinance"
        live_price = info_yf.get("regularMarketPrice") or info_yf.get("currentPrice")
        if live_price:
            result["price"] = live_price
            result["source"] = "stooq+yfinance" if result["source"] == "stooq" else "yfinance"
        if info_yf:
            result["info"] = info_yf
        if news_yf:
            result["news"] = news_yf
    except Exception:
        pass

    if result["hist"].empty:
        result["error"] = f"لم يُعثر على بيانات للرمز '{symbol}'. تأكد من الرمز والسوق."
    return result

# ═══════════════════════════════════════════════════════
# الحسابات الفنية
# ═══════════════════════════════════════════════════════

def safe(v):
    if v is None: return None
    try:
        f = float(v)
        import math
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
    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def calculate_stochastic(high, low, close, k=14, d=3):
    low_k  = low.rolling(k).min()
    high_k = high.rolling(k).max()
    stoch_k = 100 * (close - low_k) / (high_k - low_k + 1e-9)
    return stoch_k, stoch_k.rolling(d).mean()

def calculate_obv(close, volume):
    direction = close.diff().apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
    return (direction * volume).cumsum()

def detect_support_resistance(df, window=20):
    highs = df['High'].rolling(window, center=True).max()
    lows  = df['Low'].rolling(window, center=True).min()
    curr  = df['Close'].iloc[-1]
    res = sorted([v for v in highs.dropna().unique() if v > curr], )[:3]
    sup = sorted([v for v in lows.dropna().unique() if v < curr], reverse=True)[:3]
    return res, sup

def fibonacci_levels(df):
    high = df['High'].tail(60).max()
    low  = df['Low'].tail(60).min()
    diff = high - low
    return {
        "0%":    round(high, 3),
        "23.6%": round(high - 0.236 * diff, 3),
        "38.2%": round(high - 0.382 * diff, 3),
        "50%":   round(high - 0.500 * diff, 3),
        "61.8%": round(high - 0.618 * diff, 3),
        "100%":  round(low, 3),
    }

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
        "rsi": rsi, "macd": macd, "macd_sig": macd_sig, "macd_hist": macd_hist,
        "bb_upper": bb_upper, "bb_mid": bb_mid, "bb_lower": bb_lower,
        "atr": atr, "stoch_k": stoch_k, "stoch_d": stoch_d,
        "obv": obv, "sma20": sma20, "sma50": sma50, "sma200": sma200,
        "ema9": ema9, "ema21": ema21,
        "resistance": resistance, "support": support, "fibs": fibs, "volume": volume
    }


def detect_candlestick_patterns(df):
    """كشف نماذج الشموع اليابانية"""
    patterns = []
    if len(df) < 3:
        return patterns

    opens  = df['Open'].values
    highs  = df['High'].values
    lows   = df['Low'].values
    closes = df['Close'].values

    def body(i):   return abs(closes[i] - opens[i])
    def rng(i):    return highs[i] - lows[i]
    def upper(i):  return highs[i] - max(opens[i], closes[i])
    def lower(i):  return min(opens[i], closes[i]) - lows[i]
    def is_bull(i):return closes[i] > opens[i]

    i = len(closes) - 1

    # دوجي
    if rng(i) > 0 and body(i) / rng(i) < 0.1:
        patterns.append({"name":"دوجي","type":"انعكاس محتمل","signal":"محايد","bullish":None,"strength":"متوسط"})

    # مطرقة
    if is_bull(i) and lower(i) > 2*body(i) and upper(i) < 0.1*rng(i) and body(i)>0:
        patterns.append({"name":"مطرقة ↑","type":"انعكاس صعودي","signal":"شراء","bullish":True,"strength":"قوي"})

    # نجمة ساقطة
    if not is_bull(i) and upper(i) > 2*body(i) and lower(i) < 0.1*rng(i) and body(i)>0:
        patterns.append({"name":"نجمة ساقطة ↓","type":"انعكاس هبوطي","signal":"بيع","bullish":False,"strength":"قوي"})

    # ماروبوزو صاعد
    if body(i) > 0.85*rng(i) and is_bull(i):
        patterns.append({"name":"ماروبوزو صاعد ↑","type":"استمرار صعودي","signal":"شراء قوي","bullish":True,"strength":"قوي جداً"})

    # ماروبوزو هابط
    if body(i) > 0.85*rng(i) and not is_bull(i):
        patterns.append({"name":"ماروبوزو هابط ↓","type":"استمرار هبوطي","signal":"بيع قوي","bullish":False,"strength":"قوي جداً"})

    if i >= 1:
        p = i - 1
        # ابتلاع شرائي
        if not is_bull(p) and is_bull(i) and closes[i] > opens[p] and opens[i] < closes[p]:
            patterns.append({"name":"ابتلاع شرائي ↑","type":"انعكاس صعودي","signal":"شراء قوي","bullish":True,"strength":"قوي جداً"})
        # ابتلاع بيعي
        if is_bull(p) and not is_bull(i) and closes[i] < opens[p] and opens[i] > closes[p]:
            patterns.append({"name":"ابتلاع بيعي ↓","type":"انعكاس هبوطي","signal":"بيع قوي","bullish":False,"strength":"قوي جداً"})

    if i >= 2:
        a, b, c = i-2, i-1, i
        # نجمة الصباح
        if not is_bull(a) and body(b)<0.3*rng(b) and is_bull(c) and closes[c]>(opens[a]+closes[a])/2:
            patterns.append({"name":"نجمة الصباح ↑","type":"انعكاس صعودي","signal":"شراء قوي","bullish":True,"strength":"قوي جداً"})
        # نجمة المساء
        if is_bull(a) and body(b)<0.3*rng(b) and not is_bull(c) and closes[c]<(opens[a]+closes[a])/2:
            patterns.append({"name":"نجمة المساء ↓","type":"انعكاس هبوطي","signal":"بيع قوي","bullish":False,"strength":"قوي جداً"})
        # ثلاثة جنود بيض
        if all(is_bull(x) and body(x)>0.6*rng(x) for x in [a,b,c]) and closes[a]<closes[b]<closes[c]:
            patterns.append({"name":"ثلاثة جنود بيض ↑","type":"استمرار صعودي","signal":"شراء قوي","bullish":True,"strength":"قوي جداً"})
        # ثلاثة غربان سود
        if all(not is_bull(x) and body(x)>0.6*rng(x) for x in [a,b,c]) and closes[a]>closes[b]>closes[c]:
            patterns.append({"name":"ثلاثة غربان سود ↓","type":"استمرار هبوطي","signal":"بيع قوي","bullish":False,"strength":"قوي جداً"})

    if not patterns:
        bull = closes[-1] > opens[-1]
        patterns.append({"name":"شمعة " + ("صاعدة" if bull else "هابطة"),
            "type":"استمرار","signal":"استمرار الاتجاه","bullish":bull,"strength":"ضعيف"})
    return patterns


def calculate_fair_value(price, info, tech):
    """حساب السعر العادل ومناطق الدخول"""
    results = {}

    # Graham Number
    eps = info.get('trailingEps')
    bvps = info.get('bookValue')
    if eps and bvps and eps > 0 and bvps > 0:
        graham = round((22.5 * eps * bvps) ** 0.5, 3)
        results['graham'] = graham
    else:
        results['graham'] = None

    # P/E Fair Value
    pe = info.get('trailingPE')
    eps2 = info.get('trailingEps')
    sector_pe = 15
    if pe and eps2 and eps2 > 0:
        fair_pe = round(sector_pe * eps2, 3)
        results['fair_pe'] = fair_pe
    else:
        results['fair_pe'] = None

    # متوسط السعر العادل
    valid = [v for v in [results.get('graham'), results.get('fair_pe')] if v and v > 0]
    results['avg_fair'] = round(sum(valid)/len(valid), 3) if valid else None

    # مناطق الدخول من فيبوناتشي والدعم
    support = tech.get('support', [])
    fibs = tech.get('fibs', {})
    fib_levels = list(fibs.values())

    entry_zones = []
    # منطقة الدخول الأولى: عند أقرب دعم
    if support:
        entry_zones.append({
            "zone": f"منطقة شراء قوية",
            "from": round(support[0] * 0.99, 3),
            "to":   round(support[0] * 1.01, 3),
            "type": "دعم رئيسي",
            "color": "#3fb950"
        })
    if len(support) > 1:
        entry_zones.append({
            "zone": "منطقة شراء ممتازة",
            "from": round(support[1] * 0.99, 3),
            "to":   round(support[1] * 1.01, 3),
            "type": "دعم ثانوي",
            "color": "#58a6ff"
        })

    # مناطق البيع عند المقاومة
    resistance = tech.get('resistance', [])
    sell_zones = []
    if resistance:
        sell_zones.append({
            "zone": "منطقة بيع / جني أرباح",
            "from": round(resistance[0] * 0.99, 3),
            "to":   round(resistance[0] * 1.01, 3),
            "type": "مقاومة رئيسية",
            "color": "#f85149"
        })

    results['entry_zones'] = entry_zones
    results['sell_zones'] = sell_zones

    # تقييم السعر الحالي
    if results['avg_fair']:
        margin = (results['avg_fair'] - price) / price * 100
        if margin > 20:
            results['valuation'] = ("مقيَّم بأقل من قيمته ✅", "#3fb950", margin)
        elif margin > 5:
            results['valuation'] = ("يقترب من قيمته العادلة", "#d29922", margin)
        elif margin < -20:
            results['valuation'] = ("مقيَّم بأكثر من قيمته ⚠️", "#f85149", margin)
        else:
            results['valuation'] = ("عند قيمته العادلة تقريباً", "#58a6ff", margin)
    else:
        results['valuation'] = None

    return results

def generate_signals(df, tech):
    close = df['Close']
    curr  = float(close.iloc[-1])
    signals = {}
    score   = 50

    rsi_v = safe(tech['rsi'].iloc[-1])
    if rsi_v is not None:
        if rsi_v < 25:   signals['RSI'] = ('تشبع بيعي شديد ✅', 'b-green', +18)
        elif rsi_v < 35: signals['RSI'] = ('تشبع بيعي ✅', 'b-green', +12)
        elif rsi_v < 45: signals['RSI'] = ('ميل شراء', 'b-green', +5)
        elif rsi_v > 80: signals['RSI'] = ('تشبع شرائي شديد ⚠️', 'b-red', -18)
        elif rsi_v > 70: signals['RSI'] = ('تشبع شرائي ⚠️', 'b-red', -12)
        elif rsi_v > 60: signals['RSI'] = ('ميل بيع', 'b-red', -5)
        else:            signals['RSI'] = ('محايد', 'b-yellow', 0)

    mh = safe(tech['macd_hist'].iloc[-1])
    mp = safe(tech['macd_hist'].iloc[-2]) if len(tech['macd_hist']) > 1 else mh
    if mh is not None and mp is not None:
        if mh > 0 and mh > mp:   signals['MACD'] = ('تقاطع صاعد ✅', 'b-green', +15)
        elif mh > 0:              signals['MACD'] = ('إيجابي', 'b-green', +7)
        elif mh < 0 and mh < mp: signals['MACD'] = ('تقاطع هابط ⚠️', 'b-red', -15)
        else:                     signals['MACD'] = ('سلبي', 'b-red', -7)

    bbu = safe(tech['bb_upper'].iloc[-1])
    bbl = safe(tech['bb_lower'].iloc[-1])
    if bbu and bbl:
        if curr < bbl * 0.99:   signals['بولينجر'] = ('تحت النطاق - شراء ✅', 'b-green', +12)
        elif curr < bbl:        signals['بولينجر'] = ('عند الدعم', 'b-green', +6)
        elif curr > bbu * 1.01: signals['بولينجر'] = ('فوق النطاق - بيع ⚠️', 'b-red', -12)
        elif curr > bbu:        signals['بولينجر'] = ('عند المقاومة', 'b-red', -6)
        else:                   signals['بولينجر'] = ('ضمن النطاق', 'b-yellow', 0)

    s20 = safe(tech['sma20'].iloc[-1])
    s50 = safe(tech['sma50'].iloc[-1])
    s200= safe(tech['sma200'].iloc[-1])
    if s20 and s50:
        above_both = curr > s20 and curr > s50
        below_both = curr < s20 and curr < s50
        golden_cross = s20 > s50
        if above_both and golden_cross and (s200 is None or curr > s200):
            signals['المتوسطات'] = ('فوق الكل - صاعد قوي ✅', 'b-green', +15)
        elif above_both:
            signals['المتوسطات'] = ('فوق SMA20 و50 ✅', 'b-green', +8)
        elif below_both:
            signals['المتوسطات'] = ('تحت SMA20 و50 ⚠️', 'b-red', -8)
        else:
            signals['المتوسطات'] = ('مختلط', 'b-yellow', 0)

    sk = safe(tech['stoch_k'].iloc[-1])
    sd = safe(tech['stoch_d'].iloc[-1])
    if sk is not None:
        if sk < 20:   signals['ستوكاستك'] = ('تشبع بيعي ✅', 'b-green', +10)
        elif sk > 80: signals['ستوكاستك'] = ('تشبع شرائي ⚠️', 'b-red', -10)
        else:         signals['ستوكاستك'] = ('محايد', 'b-yellow', 0)

    # حجم التداول
    if 'Volume' in df.columns:
        vol_curr = df['Volume'].iloc[-1]
        vol_avg  = df['Volume'].rolling(20).mean().iloc[-1]
        if vol_curr > vol_avg * 1.5:
            signals['الحجم'] = ('ارتفاع في الحجم ✅', 'b-green', +8)
        elif vol_curr < vol_avg * 0.5:
            signals['الحجم'] = ('انخفاض في الحجم', 'b-yellow', -3)
        else:
            signals['الحجم'] = ('حجم طبيعي', 'b-yellow', 0)

    for sig in signals.values():
        score += sig[2]
    score = max(5, min(95, score))

    if   score >= 78: verdict = ('شراء قوي',  'v-strong-buy', '#3fb950')
    elif score >= 62: verdict = ('شراء',       'v-buy',        '#58a6ff')
    elif score >= 45: verdict = ('احتفاظ',     'v-hold',       '#d29922')
    elif score >= 32: verdict = ('تخفيض',      'v-reduce',     '#f0883e')
    else:             verdict = ('بيع',         'v-sell',       '#f85149')

    # حساب الأهداف
    curr_price = curr
    atr_v = safe(tech['atr'].iloc[-1]) or curr * 0.02
    resistance = tech['resistance']
    support    = tech['support']
    stop_loss  = round(support[0] * 0.99, 3) if support else round(curr * 0.95, 3)
    t1 = round(resistance[0], 3) if resistance else round(curr * 1.05, 3)
    t2 = round(resistance[1], 3) if len(resistance) > 1 else round(curr * 1.10, 3)
    t3 = round(curr * 1.15, 3)
    rr = round((t2 - curr) / (curr - stop_loss), 1) if curr > stop_loss else 1.0

    return signals, score, verdict, {
        "stop_loss": stop_loss, "t1": t1, "t2": t2, "t3": t3,
        "rr": rr, "atr": atr_v
    }

# ═══════════════════════════════════════════════════════
# تحليل الأخبار
# ═══════════════════════════════════════════════════════

POSITIVE_KW = ["profit","growth","record","increase","beat","strong","buy","upgrade","dividend","ربح","نمو","ارتفاع","قوي","شراء","توزيعات","تطور","نجاح","زيادة"]
NEGATIVE_KW = ["loss","decline","miss","weak","downgrade","sell","lawsuit","cut","warning","خسارة","انخفاض","ضعف","بيع","تراجع","قضية","غرامة","تحقيق"]

def analyze_news_sentiment(news):
    if not news: return {"score": 50, "sentiment": "محايد", "items": []}
    analyzed = []
    pos = neg = neu = 0
    for item in news:
        text = (item.get("title","") + " " + item.get("summary","")).lower()
        ph = sum(1 for k in POSITIVE_KW if k in text)
        nh = sum(1 for k in NEGATIVE_KW if k in text)
        if ph > nh: s = "إيجابي"; pos += 1
        elif nh > ph: s = "سلبي"; neg += 1
        else: s = "محايد"; neu += 1
        analyzed.append({**item, "sentiment": s})
    total = len(news)
    score = round(50 + (pos - neg) / total * 45)
    score = max(10, min(90, score))
    overall = "إيجابي" if score >= 60 else "سلبي" if score <= 40 else "محايد"
    return {"score": score, "sentiment": overall, "pos": pos, "neg": neg, "neu": neu, "items": analyzed}

# ═══════════════════════════════════════════════════════
# تقرير Claude AI
# ═══════════════════════════════════════════════════════

def predict_price_targets(price, tech, info, score):
    """توقع الأسعار المستهدفة بناءً على التحليل الفني"""
    atr = safe(tech['atr'].iloc[-1]) or price * 0.02
    resistance = tech.get('resistance', [])
    support = tech.get('support', [])
    fibs = tech.get('fibs', {})

    # أهداف صعود
    targets_up = []
    if resistance:
        for r in resistance[:3]:
            diff_pct = (r - price) / price * 100
            days = max(5, int(abs(diff_pct) / 0.3))  # تقدير عدد الأيام
            targets_up.append({
                "price": round(r, 3),
                "pct": round(diff_pct, 1),
                "days": days,
                "type": "مقاومة",
                "probability": max(30, 80 - len(targets_up) * 15)
            })

    # أهداف هبوط (وقف خسارة)
    targets_down = []
    if support:
        for s in support[:2]:
            diff_pct = (s - price) / price * 100
            targets_down.append({
                "price": round(s, 3),
                "pct": round(diff_pct, 1),
                "type": "دعم/وقف خسارة",
                "probability": 70
            })

    # هدف ATR
    atr_target = round(price + 2 * atr, 3)
    atr_pct = (atr_target - price) / price * 100
    targets_up.append({
        "price": atr_target,
        "pct": round(atr_pct, 1),
        "days": 14,
        "type": "ATR ×2",
        "probability": 60
    })

    # هدف فيبوناتشي
    fib_vals = {k: v for k, v in fibs.items() if v > price}
    if fib_vals:
        nearest_fib_level = min(fib_vals.items(), key=lambda x: x[1])
        fib_pct = (nearest_fib_level[1] - price) / price * 100
        targets_up.append({
            "price": round(nearest_fib_level[1], 3),
            "pct": round(fib_pct, 1),
            "days": max(7, int(abs(fib_pct) / 0.25)),
            "type": f"فيبوناتشي {nearest_fib_level[0]}",
            "probability": 65
        })

    # ترتيب حسب السعر
    targets_up = sorted([t for t in targets_up if t['pct'] > 0], key=lambda x: x['price'])[:4]
    targets_down = sorted(targets_down, key=lambda x: x['price'], reverse=True)[:2]

    return targets_up, targets_down


def generate_ai_analysis(symbol, price, currency, score, verdict_text, signals, tech, info, news_sent, api_key):
    if not api_key:
        return _smart_report(symbol, price, currency, score, verdict_text, signals, tech, info, news_sent)

    rsi_v   = safe(tech['rsi'].iloc[-1]) or 50
    macd_v  = safe(tech['macd_hist'].iloc[-1]) or 0
    s20     = safe(tech['sma20'].iloc[-1])
    s50     = safe(tech['sma50'].iloc[-1])
    pe      = info.get('trailingPE','—')
    sector  = info.get('sector','—')
    market_cap = info.get('marketCap', 0)
    resistance = tech.get('resistance', [])
    support    = tech.get('support', [])

    prompt = f"""أنت محلل مالي خبير متخصص في الأسواق الخليجية والأمريكية.
حلّل هذا السهم بدقة وقدّم تقريراً احترافياً شاملاً بالعربية.

═══ بيانات السهم ═══
السهم: {symbol} | السعر الحالي: {price:.3f} {currency}
القطاع: {sector} | P/E: {pe} | القيمة السوقية: {f"{market_cap/1e9:.1f}B" if market_cap else "—"}

═══ التحليل الفني (درجة: {score}/100) ═══
• RSI(14): {rsi_v:.1f} — {'⚠️ تشبع شرائي' if rsi_v > 70 else '✅ تشبع بيعي' if rsi_v < 30 else 'محايد'}
• MACD Histogram: {macd_v:.4f} ({'زخم صاعد ✅' if macd_v > 0 else 'زخم هابط ⚠️'})
• SMA20: {f"{s20:.3f}" if s20 else "—"} | SMA50: {f"{s50:.3f}" if s50 else "—"}
• المقاومة الأولى: {resistance[0]:.3f if resistance else "—"}
• الدعم الأول: {support[0]:.3f if support else "—"}
• الإشارات: {", ".join([f"{k}: {v[0]}" for k, v in list(signals.items())[:5]])}

═══ التوصية والأخبار ═══
• التوصية الحالية: {verdict_text} (درجة ثقة: {score}/100)
• مشاعر الأخبار: {news_sent.get("sentiment","—")} (درجة: {news_sent.get("score",50)}/100)

قدّم التقرير بهذا الهيكل بالضبط:

## الملخص التنفيذي
[3-4 جمل تشرح الوضع الحالي للسهم]

## التوقعات السعرية
• **السعر المتوقع خلال أسبوع:** [سعر محدد] {currency} (احتمالية [X]%)
• **السعر المتوقع خلال شهر:** [سعر محدد] {currency} (احتمالية [X]%)
• **السعر المتوقع خلال 3 أشهر:** [سعر محدد] {currency} (احتمالية [X]%)

## أهداف الصعود
• الهدف الأول: [سعر] — [مبرر]
• الهدف الثاني: [سعر] — [مبرر]
• الهدف الثالث: [سعر] — [مبرر]

## وقف الخسارة المقترح
• وقف الخسارة: [سعر] ({currency}) — [مبرر]

## المحفزات الرئيسية ✅
• [محفز 1 بالأرقام الفعلية]
• [محفز 2]
• [محفز 3]

## المخاطر ⚠️
• [خطر 1]
• [خطر 2]
• [خطر 3]

## التوصية النهائية
[توصية واضحة ومفصّلة مع مبررها]"""

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"Content-Type":"application/json","x-api-key":api_key,"anthropic-version":"2023-06-01"},
            json={"model":"claude-sonnet-4-6","max_tokens":2000,
                  "system":"أنت محلل مالي خبير. أجب بالعربية فقط. استخدم الأرقام الفعلية المقدمة في تحليلك.",
                  "messages":[{"role":"user","content":prompt}]},
            timeout=35
        )
        resp.raise_for_status()
        return resp.json()["content"][0]["text"]
    except Exception:
        return _smart_report(symbol, price, currency, score, verdict_text, signals, tech, info, news_sent)

def _smart_report(symbol, price, currency, score, verdict_text, signals, tech, info, news_sent):
    rsi_v  = safe(tech['rsi'].iloc[-1]) or 50
    macd_v = safe(tech['macd_hist'].iloc[-1]) or 0
    s20    = safe(tech['sma20'].iloc[-1])
    s50    = safe(tech['sma50'].iloc[-1])
    atr_v  = safe(tech['atr'].iloc[-1]) or price * 0.02
    res    = tech.get('resistance', [])
    sup    = tech.get('support', [])

    catalysts = []
    risks = []

    if rsi_v < 35: catalysts.append(f"RSI={rsi_v:.1f} في منطقة تشبع بيعي — فرصة دخول جيدة")
    if rsi_v < 45: catalysts.append(f"RSI={rsi_v:.1f} في منطقة منخفضة — مجال للصعود")
    if macd_v > 0: catalysts.append(f"MACD إيجابي ({macd_v:.4f}) — زخم صاعد مؤكد")
    if s20 and price > s20: catalysts.append(f"السعر {price:.3f} فوق SMA20 ({s20:.3f}) — اتجاه قصير المدى صاعد")
    if s50 and price > s50: catalysts.append(f"السعر فوق SMA50 ({s50:.3f}) — اتجاه متوسط المدى صاعد")
    if sup: catalysts.append(f"دعم قوي عند {sup[0]:.3f} يحمي من الهبوط الحاد")

    if rsi_v > 70: risks.append(f"RSI={rsi_v:.1f} في منطقة تشبع شرائي — احتمال تصحيح")
    if macd_v < 0: risks.append(f"MACD سلبي ({macd_v:.4f}) — ضغط بيعي مستمر")
    if s20 and price < s20: risks.append(f"السعر {price:.3f} تحت SMA20 ({s20:.3f}) — ضعف قصير المدى")
    if s50 and price < s50: risks.append(f"السعر تحت SMA50 ({s50:.3f}) — ضعف متوسط المدى")
    if res: risks.append(f"مقاومة قوية عند {res[0]:.3f} قد تحد من الصعود")

    if not catalysts: catalysts = ["مؤشرات فنية في مستوى مقبول","إمكانية تحسن على المدى القريب","قوة السوق العامة"]
    if not risks: risks = ["مخاطر السوق العامة","تقلبات الأسعار الطبيعية","عدم اليقين الاقتصادي"]

    # التوقعات السعرية
    target_week  = round(price + atr_v * 1.5, 3)
    target_month = round(price + atr_v * 3.0, 3)
    target_3m    = round(price + atr_v * 6.0, 3)
    stop_loss    = round(sup[0] * 0.985, 3) if sup else round(price * 0.95, 3)

    if score < 45:  # هبوطي
        target_week  = round(price - atr_v * 1.5, 3)
        target_month = round(price - atr_v * 2.5, 3)
        target_3m    = round(price - atr_v * 4.0, 3)

    t1_price = round(res[0], 3) if res else target_week
    t2_price = round(res[1], 3) if len(res) > 1 else target_month
    t3_price = round(price * (1.15 if score >= 60 else 0.88), 3)

    news_color = "إيجابية" if news_sent.get('score',50) >= 60 else "سلبية" if news_sent.get('score',50) <= 40 else "محايدة"
    trend_text = "صاعد" if s20 and price > s20 else "هابط" if s20 and price < s20 else "جانبي"

    report = f"""## 📊 تقرير التحليل الذكي — {symbol}

### الملخص التنفيذي
سهم **{symbol}** يُسجّل درجة تقنية **{score}/100** مع توصية **{verdict_text}**.
الاتجاه العام **{trend_text}** — السعر الحالي {price:.3f} {currency}.
الأخبار {news_color} (درجة {news_sent.get('score',50)}/100). {'ننصح بالدخول عند مستويات الدعم.' if score >= 60 else 'ننصح بالحذر والانتظار لتأكيد الاتجاه.'}

---

### 📈 التوقعات السعرية
| الفترة | السعر المتوقع | التغير |
|--------|--------------|--------|
| أسبوع واحد | **{target_week:.3f} {currency}** | {(target_week-price)/price*100:+.1f}% |
| شهر واحد | **{target_month:.3f} {currency}** | {(target_month-price)/price*100:+.1f}% |
| 3 أشهر | **{target_3m:.3f} {currency}** | {(target_3m-price)/price*100:+.1f}% |

### 🎯 أهداف الصعود
- **الهدف الأول:** {t1_price:.3f} {currency} ({(t1_price-price)/price*100:+.1f}%) — {'مقاومة رئيسية' if res else 'ATR ×1.5'}
- **الهدف الثاني:** {t2_price:.3f} {currency} ({(t2_price-price)/price*100:+.1f}%) — {'مقاومة ثانية' if len(res)>1 else 'ATR ×3'}
- **الهدف الثالث:** {t3_price:.3f} {currency} ({(t3_price-price)/price*100:+.1f}%) — هدف مدى متوسط

### 🛑 وقف الخسارة المقترح
- **وقف الخسارة:** {stop_loss:.3f} {currency} ({(stop_loss-price)/price*100:+.1f}%) — {'تحت الدعم الرئيسي' if sup else 'نسبة ثابتة 5%'}

### ✅ المحفزات الرئيسية
{chr(10).join([f'- {c}' for c in catalysts[:4]])}

### ⚠️ المخاطر
{chr(10).join([f'- {r}' for r in risks[:4]])}

### 📋 التوصية النهائية
**{verdict_text}** — بناءً على التحليل الفني المتكامل (درجة {score}/100).
{'نسبة المخاطرة/العائد: 1:' + str(round((t2_price-price)/(price-stop_loss),1)) if price > stop_loss else ''}
{'يُنصح بالدخول على مستويات: ' + str(sup[0]) + ' — ' + str(round(sup[0]*1.01,3)) + ' ' + currency if sup and score >= 60 else 'يُنصح بالانتظار لتأكيد الاتجاه قبل الدخول.'}
"""
    return report

# ═══════════════════════════════════════════════════════
# الرسم البياني
# ═══════════════════════════════════════════════════════

def build_chart(df, tech, symbol, show_vol=True):
    rows = 4 if show_vol else 3
    heights = [0.50, 0.18, 0.17, 0.15] if show_vol else [0.55, 0.23, 0.22]
    specs = [[{"secondary_y": False}]] * rows

    fig = make_subplots(
        rows=rows, cols=1, shared_xaxes=True,
        vertical_spacing=0.02,
        row_heights=heights,
        subplot_titles=("", "RSI", "MACD", "حجم التداول") if show_vol else ("", "RSI", "MACD")
    )

    # شموع
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'],
        low=df['Low'], close=df['Close'], name="السعر",
        increasing=dict(line=dict(color='#3fb950', width=1), fillcolor='#3fb950'),
        decreasing=dict(line=dict(color='#f85149', width=1), fillcolor='#f85149'),
    ), row=1, col=1)

    # المتوسطات
    for name_ma, col_ma, w in [('SMA20','#58a6ff',1.5),('SMA50','#d29922',1.5),('SMA200','#f0883e',1.5)]:
        key = name_ma.lower().replace('sma','sma')
        val = tech.get(f'sma{name_ma[3:]}')
        if val is not None and not val.isna().all():
            fig.add_trace(go.Scatter(x=df.index, y=val, name=name_ma,
                line=dict(color=col_ma, width=w)), row=1, col=1)

    # بولينجر
    if not tech['bb_upper'].isna().all():
        fig.add_trace(go.Scatter(x=df.index, y=tech['bb_upper'], name='BB↑',
            line=dict(color='#bc8cff', width=1, dash='dash')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=tech['bb_lower'], name='BB↓',
            line=dict(color='#bc8cff', width=1, dash='dash'),
            fill='tonexty', fillcolor='rgba(188,140,255,0.06)'), row=1, col=1)

    # دعم ومقاومة
    curr = float(df['Close'].iloc[-1])
    for r in tech['resistance'][:2]:
        if r: fig.add_hline(y=r, line=dict(color='#f85149', width=1, dash='dot'), row=1, col=1)
    for s in tech['support'][:2]:
        if s: fig.add_hline(y=s, line=dict(color='#3fb950', width=1, dash='dot'), row=1, col=1)

    # RSI
    fig.add_trace(go.Scatter(x=df.index, y=tech['rsi'], name='RSI',
        line=dict(color='#58a6ff', width=2)), row=2, col=1)
    fig.add_hline(y=70, line=dict(color='#f85149', width=1, dash='dot'), row=2, col=1)
    fig.add_hline(y=30, line=dict(color='#3fb950', width=1, dash='dot'), row=2, col=1)
    fig.add_hrect(y0=70, y1=100, fillcolor='rgba(248,81,73,0.07)', line_width=0, row=2, col=1)
    fig.add_hrect(y0=0,  y1=30,  fillcolor='rgba(63,185,80,0.07)',  line_width=0, row=2, col=1)

    # MACD
    colors_macd = ['#3fb950' if v >= 0 else '#f85149' for v in tech['macd_hist'].fillna(0)]
    fig.add_trace(go.Bar(x=df.index, y=tech['macd_hist'], name='MACD Hist',
        marker_color=colors_macd, opacity=0.7), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=tech['macd'], name='MACD',
        line=dict(color='#58a6ff', width=1.5)), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=tech['macd_sig'], name='إشارة',
        line=dict(color='#f0883e', width=1.5)), row=3, col=1)

    # الحجم
    if show_vol and 'Volume' in df.columns:
        vol_colors = ['#3fb950' if df['Close'].iloc[i] >= df['Open'].iloc[i] else '#f85149'
                      for i in range(len(df))]
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='الحجم',
            marker_color=vol_colors, opacity=0.6), row=4, col=1)

    fig.update_layout(
        paper_bgcolor='#0d1117', plot_bgcolor='#0d1117',
        font=dict(color='#e6edf3', family='Cairo'),
        height=750, margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation='h', y=1.04, x=0,
            bgcolor='rgba(22,27,34,0.9)', bordercolor='#30363d', borderwidth=1, font=dict(size=10)),
        xaxis_rangeslider_visible=False,
        hovermode='x unified',
    )
    for i in range(1, rows+1):
        ax = 'xaxis' if i == 1 else f'xaxis{i}'
        ya = 'yaxis' if i == 1 else f'yaxis{i}'
        fig.update_layout(**{
            ax: dict(gridcolor='#21262d', gridwidth=0.5, showgrid=True, zeroline=False, tickfont=dict(size=9)),
            ya: dict(gridcolor='#21262d', gridwidth=0.5, showgrid=True, zeroline=False, side='right', tickfont=dict(size=9)),
        })
    fig.update_layout(yaxis2=dict(range=[0, 100]))
    return fig

# ═══════════════════════════════════════════════════════
# الواجهة الرئيسية
# ═══════════════════════════════════════════════════════

st.markdown("""
<div class="pro-header">
  <h1>📊 محلل الأسهم الذكي Pro v3</h1>
  <p>محفظة • تنبيهات • أخبار • AI • تحليل شامل • 10 أسواق عالمية • بيانات لحظية</p>
</div>
""", unsafe_allow_html=True)

nav = st.radio("", ["🔍 تحليل", "⚖️ مقارنة", "💼 المحفظة", "🔔 التنبيهات", "👁️ المراقبة", "📜 السجل"],
    horizontal=True, label_visibility="collapsed")

st.divider()

MARKETS = {
    "🇸🇦 السوق السعودي (TASI)": "sa",
    "🇺🇸 الأمريكي (NYSE/NASDAQ)": "us",
    "🇦🇪 الإماراتي (DFM/ADX)": "ae",
    "🇶🇦 القطري (QE)": "qa",
    "🇰🇼 الكويتي": "kw",
    "🇧🇭 البحريني": "bh",
    "🇯🇴 الأردني": "jo",
    "🇪🇬 المصري (EGX)": "eg",
    "🇬🇧 البريطاني (LSE)": "gb",
    "🇩🇪 الألماني (XETRA)": "de",
}

# ── صفحة التحليل ──────────────────────────────────────
if nav == "🔍 تحليل":

    with st.sidebar:
        st.markdown("### ⚙️ الإعدادات")
        api_key = st.text_input("🤖 مفتاح Claude AI (اختياري)", type="password",
            placeholder="sk-ant-...", help="لتفعيل التقارير الذكية المتقدمة")
        show_vol = st.checkbox("عرض حجم التداول", value=True)
        st.markdown("---")
        st.markdown("### 📌 أسهم محفوظة")
        if 'watchlist' not in st.session_state:
            st.session_state.watchlist = [("2222","sa"),("1120","sa"),("AAPL","us")]
        for sym, mkt in st.session_state.watchlist:
            if st.button(f"📈 {sym}", key=f"wl_{sym}"):
                st.session_state['q_sym'] = sym
                st.session_state['q_mkt'] = mkt
                st.rerun()

    col_sym, col_mkt, col_btn = st.columns([3,2,1])
    with col_sym:
        symbol = st.text_input("🔍 رمز السهم", placeholder="مثال: 2222 أو AAPL",
            label_visibility="collapsed").strip().upper()
    with col_mkt:
        market_label = st.selectbox("السوق", list(MARKETS.keys()), label_visibility="collapsed")
        market = MARKETS[market_label]
    with col_btn:
        analyze = st.button("📊 تحليل السهم", use_container_width=True)

    # أسهم سريعة
    st.markdown("**⚡ أسهم سريعة:**")
    qcols = st.columns(10)
    quick = [("2222","sa"),("1120","sa"),("7010","sa"),("2010","sa"),("1010","sa"),
             ("AAPL","us"),("NVDA","us"),("TSLA","us"),("MSFT","us"),("AMZN","us")]
    for i,(sym,mkt) in enumerate(quick):
        with qcols[i]:
            if st.button(sym, key=f"q_{sym}"):
                st.session_state['q_sym'] = sym
                st.session_state['q_mkt'] = mkt
                st.rerun()

    if 'q_sym' in st.session_state:
        symbol = st.session_state.pop('q_sym')
        market = st.session_state.pop('q_mkt','sa')
        analyze = True

    if analyze and symbol:
        with st.spinner(f"⏳ جاري تحليل {symbol}..."):
            data = get_stock_data(symbol, market)

        if data['error']:
            st.error(f"❌ {data['error']}")
            st.stop()

        df      = data['hist']
        info    = data['info']
        news    = data['news']
        price   = data['price'] or float(df['Close'].iloc[-1])
        source  = data['source']

        prev    = float(df['Close'].iloc[-2]) if len(df) > 1 else price
        change  = price - prev
        chg_pct = (change / prev * 100) if prev else 0
        name    = info.get('longName') or info.get('shortName') or symbol
        currency= info.get('currency','SAR' if market=='sa' else 'USD')

        tech = analyze_technicals(df)
        signals, score, verdict, targets = generate_signals(df, tech)
        news_sent = analyze_news_sentiment(news)

        # Header السهم
        up = change >= 0
        st.markdown(f"""
        <div class="card">
          <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:1rem">
            <div>
              <div style="font-size:1.4rem;font-weight:900">{name}</div>
              <div style="color:#8b949e;font-size:.85rem">{symbol} · {market_label.split('(')[0].strip()}</div>
              <div style="margin-top:.4rem">
                <span class="badge b-blue">مصدر: {source}</span>
                <span class="badge {'b-green' if score>=60 else 'b-red' if score<40 else 'b-yellow'}" style="margin-right:.4rem">
                  درجة: {score}/100
                </span>
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
        """, unsafe_allow_html=True)

        # مؤشرات سريعة
        rsi_v = safe(tech['rsi'].iloc[-1])
        atr_v = safe(tech['atr'].iloc[-1])
        vol_v = df['Volume'].iloc[-1] if 'Volume' in df.columns else 0
        mc    = info.get('marketCap', 0)

        cols6 = st.columns(6)
        mets  = [
            ("الدرجة الكلية", f"{score}/100", '#3fb950' if score>=60 else '#f85149' if score<40 else '#d29922'),
            ("RSI(14)", f"{rsi_v:.1f}" if rsi_v else "—", '#3fb950' if rsi_v and rsi_v<30 else '#f85149' if rsi_v and rsi_v>70 else '#58a6ff'),
            ("ATR(14)", f"{atr_v:.3f}" if atr_v else "—", '#8b949e'),
            ("مشاعر الأخبار", f"{news_sent['score']}/100", '#3fb950' if news_sent['score']>=60 else '#f85149' if news_sent['score']<=40 else '#d29922'),
            ("حجم التداول", f"{vol_v/1e6:.1f}M" if vol_v>=1e6 else f"{int(vol_v):,}", '#8b949e'),
            ("القيمة السوقية", f"{mc/1e9:.1f}B" if mc else "—", '#8b949e'),
        ]
        for col, (lbl, val, clr) in zip(cols6, mets):
            with col:
                st.markdown(f"""<div class="metric-card">
                  <div class="metric-val" style="color:{clr}">{val}</div>
                  <div class="metric-lbl">{lbl}</div>
                </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # التبويبات
        tab_chart, tab_rec, tab_tech, tab_ai, tab_news, tab_info, tab_fib = st.tabs([
            "📈 الرسم البياني", "🎯 التوصية", "📊 التحليل الفني",
            "🤖 تقرير AI", "📰 الأخبار", "ℹ️ معلومات", "📐 فيبوناتشي"
        ])

        with tab_chart:
            fig = build_chart(df, tech, symbol, show_vol)
            st.plotly_chart(fig, use_container_width=True,
                config={"displayModeBar":True,"displaylogo":False,
                        "modeBarButtonsToRemove":["lasso2d","select2d"]})

        with tab_rec:
            # حساب السعر العادل والشموع
            candles = detect_candlestick_patterns(df)
            fair_val = calculate_fair_value(price, info, tech)

            st.markdown(f"""
            <div class="verdict-box {verdict[1]}">
              <div class="verdict-title" style="color:{verdict[2]}">{verdict[0]}</div>
              <div class="verdict-sub">درجة الثقة: {score}/100 | نسبة المخاطرة/العائد: 1:{targets['rr']}</div>
            </div>
            """, unsafe_allow_html=True)

            c1,c2,c3,c4,c5 = st.columns(5)
            tgt_items = [
                (c1, "سعر الدخول", f"{price:.3f}", '#58a6ff'),
                (c2, "وقف الخسارة", f"{targets['stop_loss']:.3f}", '#f85149'),
                (c3, "الهدف 1", f"{targets['t1']:.3f}", '#3fb950'),
                (c4, "الهدف 2", f"{targets['t2']:.3f}", '#3fb950'),
                (c5, "الهدف 3", f"{targets['t3']:.3f}", '#bc8cff'),
            ]
            for col, lbl, val, clr in tgt_items:
                with col:
                    st.markdown(f"""<div class="metric-card">
                      <div class="metric-val" style="color:{clr}">{val}</div>
                      <div class="metric-lbl">{lbl}</div>
                    </div>""", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("### 📡 الإشارات التفصيلية")
            sig_cols = st.columns(len(signals))
            for i,(k,v) in enumerate(signals.items()):
                with sig_cols[i]:
                    st.markdown(f"""<div class="metric-card" style="text-align:center">
                      <div style="font-size:.78rem;color:#8b949e;margin-bottom:.3rem">{k}</div>
                      <span class="badge {v[1]}">{v[0]}</span>
                    </div>""", unsafe_allow_html=True)

            # ── السعر العادل ──────────────────────────────────
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("### 💰 السعر العادل والتقييم")

            fv_cols = st.columns(4)
            with fv_cols[0]:
                graham = fair_val.get('graham')
                st.markdown(f"""<div class="metric-card">
                  <div class="metric-val" style="color:#bc8cff">{graham:.3f if graham else '—'}</div>
                  <div class="metric-lbl">Graham Number</div>
                </div>""", unsafe_allow_html=True)
            with fv_cols[1]:
                fair_pe = fair_val.get('fair_pe')
                st.markdown(f"""<div class="metric-card">
                  <div class="metric-val" style="color:#58a6ff">{fair_pe:.3f if fair_pe else '—'}</div>
                  <div class="metric-lbl">قيمة P/E العادلة</div>
                </div>""", unsafe_allow_html=True)
            with fv_cols[2]:
                avg_fair = fair_val.get('avg_fair')
                st.markdown(f"""<div class="metric-card">
                  <div class="metric-val" style="color:#d29922">{avg_fair:.3f if avg_fair else '—'}</div>
                  <div class="metric-lbl">متوسط السعر العادل</div>
                </div>""", unsafe_allow_html=True)
            with fv_cols[3]:
                val_tuple = fair_val.get('valuation')
                if val_tuple:
                    val_text, val_color, val_margin = val_tuple
                    st.markdown(f"""<div class="metric-card">
                      <div class="metric-val" style="color:{val_color};font-size:1rem">{val_text}</div>
                      <div class="metric-lbl">هامش الأمان: {val_margin:+.1f}%</div>
                    </div>""", unsafe_allow_html=True)

            # ── مناطق الدخول والخروج ──────────────────────────────
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("### 🎯 مناطق الدخول والخروج")
            ez1, ez2 = st.columns(2)
            with ez1:
                st.markdown("**🟢 مناطق الشراء**")
                for z in fair_val.get('entry_zones', []):
                    st.markdown(f"""
                    <div style="background:rgba(63,185,80,0.1);border:1px solid #3fb950;
                         border-radius:8px;padding:.7rem;margin-bottom:.5rem">
                      <div style="color:#3fb950;font-weight:700">{z['zone']}</div>
                      <div style="color:#e6edf3">من <strong>{z['from']:.3f}</strong> إلى <strong>{z['to']:.3f}</strong></div>
                      <div style="color:#8b949e;font-size:.8rem">{z['type']}</div>
                    </div>""", unsafe_allow_html=True)
                if not fair_val.get('entry_zones'):
                    st.info("لا توجد مناطق دخول محددة حالياً")
            with ez2:
                st.markdown("**🔴 مناطق الخروج/البيع**")
                for z in fair_val.get('sell_zones', []):
                    st.markdown(f"""
                    <div style="background:rgba(248,81,73,0.1);border:1px solid #f85149;
                         border-radius:8px;padding:.7rem;margin-bottom:.5rem">
                      <div style="color:#f85149;font-weight:700">{z['zone']}</div>
                      <div style="color:#e6edf3">من <strong>{z['from']:.3f}</strong> إلى <strong>{z['to']:.3f}</strong></div>
                      <div style="color:#8b949e;font-size:.8rem">{z['type']}</div>
                    </div>""", unsafe_allow_html=True)

            # ── الشموع اليابانية ──────────────────────────────────
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("### 🕯️ نماذج الشموع اليابانية")
            if candles:
                candle_cols = st.columns(min(len(candles), 3))
                for i, c in enumerate(candles[:3]):
                    bull = c.get('bullish')
                    clr  = '#3fb950' if bull else '#f85149' if bull is False else '#d29922'
                    icon = '↑' if bull else '↓' if bull is False else '↔'
                    with candle_cols[i % 3]:
                        st.markdown(f"""
                        <div class="metric-card" style="border-color:{clr}">
                          <div style="font-size:1.1rem;font-weight:700;color:{clr}">{icon} {c['name']}</div>
                          <div style="color:#8b949e;font-size:.78rem;margin:.3rem 0">{c['type']}</div>
                          <span class="badge" style="background:rgba(0,0,0,.3);color:{clr};border:1px solid {clr}">
                            {c['signal']}
                          </span>
                          <div style="color:#8b949e;font-size:.75rem;margin-top:.3rem">قوة: {c['strength']}</div>
                        </div>""", unsafe_allow_html=True)

            # الدعم والمقاومة
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("### 📍 الدعم والمقاومة")
            sr1, sr2 = st.columns(2)
            with sr1:
                st.markdown("**🔴 المقاومة**")
                for r in tech['resistance']:
                    diff = (r - price) / price * 100
                    st.markdown(f"`{r:.3f}` ← ({diff:+.1f}%)")
            with sr2:
                st.markdown("**🟢 الدعم**")
                for s in tech['support']:
                    diff = (s - price) / price * 100
                    st.markdown(f"`{s:.3f}` ← ({diff:+.1f}%)")

            # إضافة للمحفظة
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button(f"➕ إضافة {symbol} للمحفظة المراقَبة", use_container_width=True):
                entry = (symbol, market)
                if entry not in st.session_state.get('watchlist', []):
                    if 'watchlist' not in st.session_state:
                        st.session_state.watchlist = []
                    st.session_state.watchlist.append(entry)
                    st.success(f"✅ تمت إضافة {symbol} للقائمة")

        with tab_tech:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**المؤشرات الفنية**")
                ind = [
                    ("RSI(14)", f"{safe(tech['rsi'].iloc[-1]):.1f}" if safe(tech['rsi'].iloc[-1]) else "—"),
                    ("MACD", f"{safe(tech['macd'].iloc[-1]):.4f}" if safe(tech['macd'].iloc[-1]) else "—"),
                    ("MACD Signal", f"{safe(tech['macd_sig'].iloc[-1]):.4f}" if safe(tech['macd_sig'].iloc[-1]) else "—"),
                    ("MACD Hist", f"{safe(tech['macd_hist'].iloc[-1]):.4f}" if safe(tech['macd_hist'].iloc[-1]) else "—"),
                    ("Stoch K", f"{safe(tech['stoch_k'].iloc[-1]):.1f}" if safe(tech['stoch_k'].iloc[-1]) else "—"),
                    ("Stoch D", f"{safe(tech['stoch_d'].iloc[-1]):.1f}" if safe(tech['stoch_d'].iloc[-1]) else "—"),
                ]
                for lbl, val in ind:
                    st.markdown(f"**{lbl}:** `{val}`")
            with c2:
                st.markdown("**المتوسطات المتحركة**")
                mas = [
                    ("SMA(9)", f"{safe(tech['ema9'].iloc[-1]):.3f}" if safe(tech['ema9'].iloc[-1]) else "—"),
                    ("SMA(20)", f"{safe(tech['sma20'].iloc[-1]):.3f}" if safe(tech['sma20'].iloc[-1]) else "—"),
                    ("SMA(50)", f"{safe(tech['sma50'].iloc[-1]):.3f}" if safe(tech['sma50'].iloc[-1]) else "—"),
                    ("SMA(200)", f"{safe(tech['sma200'].iloc[-1]):.3f}" if safe(tech['sma200'].iloc[-1]) else "—"),
                    ("BB Upper", f"{safe(tech['bb_upper'].iloc[-1]):.3f}" if safe(tech['bb_upper'].iloc[-1]) else "—"),
                    ("BB Lower", f"{safe(tech['bb_lower'].iloc[-1]):.3f}" if safe(tech['bb_lower'].iloc[-1]) else "—"),
                    ("ATR(14)", f"{safe(tech['atr'].iloc[-1]):.3f}" if safe(tech['atr'].iloc[-1]) else "—"),
                ]
                for lbl, val in mas:
                    st.markdown(f"**{lbl}:** `{val}`")

        with tab_ai:
            st.markdown("### 🤖 تقرير الذكاء الاصطناعي — التوقعات السعرية")
            if not api_key:
                st.info("💡 أضف مفتاح Claude AI في الشريط الجانبي للحصول على توقعات سعرية أكثر دقة وتفصيلاً.")

            # عرض التوقعات السعرية الآلية أولاً
            targets_up, targets_down = predict_price_targets(price, tech, info, score)

            st.markdown("#### 📈 التوقعات السعرية (تحليل آلي)")
            tup_cols = st.columns(min(len(targets_up), 4))
            for i, t in enumerate(targets_up[:4]):
                with tup_cols[i]:
                    prob_color = '#3fb950' if t['probability'] >= 65 else '#d29922' if t['probability'] >= 50 else '#8b949e'
                    st.markdown(f"""<div class="metric-card" style="border-color:#3fb950">
                      <div style="color:#8b949e;font-size:.72rem;margin-bottom:.2rem">{t['type']}</div>
                      <div class="metric-val" style="color:#3fb950">{t['price']:.3f}</div>
                      <div style="color:#e6edf3;font-size:.85rem">{t['pct']:+.1f}%</div>
                      <div style="color:{prob_color};font-size:.78rem">احتمالية: {t['probability']}%</div>
                      <div style="color:#8b949e;font-size:.72rem">خلال ~{t['days']} يوم</div>
                    </div>""", unsafe_allow_html=True)

            if targets_down:
                st.markdown("#### 🛑 مستويات الدعم/وقف الخسارة")
                td_cols = st.columns(len(targets_down))
                for i, t in enumerate(targets_down):
                    with td_cols[i]:
                        st.markdown(f"""<div class="metric-card" style="border-color:#f85149">
                          <div style="color:#8b949e;font-size:.72rem;margin-bottom:.2rem">{t['type']}</div>
                          <div class="metric-val" style="color:#f85149">{t['price']:.3f}</div>
                          <div style="color:#e6edf3;font-size:.85rem">{t['pct']:+.1f}%</div>
                        </div>""", unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("#### 📋 التقرير التفصيلي")
            with st.spinner("🤖 جاري توليد التقرير..."):
                ai_report = generate_ai_analysis(
                    symbol, price, currency, score, verdict[0],
                    signals, tech, info, news_sent, api_key
                )
            st.markdown(f'<div class="ai-box">{ai_report}</div>', unsafe_allow_html=True)

        with tab_news:
            st.markdown(f"""
            ### 📰 تحليل الأخبار
            **المشاعر العامة:** `{news_sent['sentiment']}` | الدرجة: **{news_sent['score']}/100**
            | إيجابي: {news_sent['pos']} | سلبي: {news_sent['neg']} | محايد: {news_sent['neu']}
            """)
            if news_sent['items']:
                for item in news_sent['items']:
                    color = '#3fb950' if item['sentiment']=='إيجابي' else '#f85149' if item['sentiment']=='سلبي' else '#8b949e'
                    st.markdown(f"""
                    <div class="news-item">
                      <span class="badge" style="background:rgba(0,0,0,.3);color:{color};border:1px solid {color}">
                        {item['sentiment']}
                      </span>
                      <strong style="margin-right:.4rem">{item.get('title','')}</strong>
                      <div style="color:#8b949e;font-size:.78rem;margin-top:.3rem">{item.get('date','')}</div>
                    </div>""", unsafe_allow_html=True)
            else:
                st.info("لا تتوفر أخبار حالياً لهذا السهم.")

        with tab_info:
            if info:
                st.markdown("### ℹ️ معلومات الشركة")
                fields = [
                    ("الاسم الكامل",    info.get('longName','—')),
                    ("القطاع",          info.get('sector','—')),
                    ("الصناعة",         info.get('industry','—')),
                    ("البورصة",         info.get('exchange','—')),
                    ("العملة",          info.get('currency','—')),
                    ("الدولة",          info.get('country','—')),
                    ("الموظفون",        f"{info.get('fullTimeEmployees',0):,}" if info.get('fullTimeEmployees') else '—'),
                    ("القيمة السوقية",  f"{info.get('marketCap',0)/1e9:.2f}B" if info.get('marketCap') else '—'),
                    ("P/E الحالي",      f"{info.get('trailingPE','—'):.2f}" if isinstance(info.get('trailingPE'),float) else '—'),
                    ("P/E المستقبلي",   f"{info.get('forwardPE','—'):.2f}" if isinstance(info.get('forwardPE'),float) else '—'),
                    ("P/B",             f"{info.get('priceToBook','—'):.2f}" if isinstance(info.get('priceToBook'),float) else '—'),
                    ("EPS",             f"{info.get('trailingEps','—'):.3f}" if isinstance(info.get('trailingEps'),float) else '—'),
                    ("هامش الربح",      f"{info.get('profitMargins',0)*100:.1f}%" if info.get('profitMargins') else '—'),
                    ("عائد التوزيعات",  f"{info.get('dividendYield',0)*100:.2f}%" if info.get('dividendYield') else '—'),
                    ("أعلى 52 أسبوع",  f"{info.get('fiftyTwoWeekHigh','—'):.3f}" if isinstance(info.get('fiftyTwoWeekHigh'),float) else '—'),
                    ("أدنى 52 أسبوع",  f"{info.get('fiftyTwoWeekLow','—'):.3f}" if isinstance(info.get('fiftyTwoWeekLow'),float) else '—'),
                ]
                c1, c2 = st.columns(2)
                for i,(lbl,val) in enumerate(fields):
                    with (c1 if i%2==0 else c2):
                        st.markdown(f"**{lbl}:** `{val}`")
                desc = info.get('longBusinessSummary','')
                if desc:
                    with st.expander("📝 نبذة عن الشركة"):
                        st.write(desc[:800])
            else:
                st.info("ℹ️ المعلومات التفصيلية غير متاحة لهذا السهم من Stooq. جرب سهماً أمريكياً.")

        with tab_fib:
            st.markdown("### 📐 مستويات فيبوناتشي مع مناطق الشراء والبيع")
            fibs = tech['fibs']
            curr_p = price

            # شرح مختصر
            st.markdown("""
            > **دليل القراءة:** مستويات Fib 38.2% و50% و61.8% هي **مناطق دعم وشراء** محتملة.
            > مستوى Fib 0% هو **مقاومة** رئيسية.
            """)

            fib_zones = {
                "0%":    ("مقاومة رئيسية — منطقة بيع/جني أرباح", "#f85149"),
                "23.6%": ("دعم خفيف — مراقبة", "#f0883e"),
                "38.2%": ("دعم متوسط — منطقة شراء محتملة ⭐", "#d29922"),
                "50%":   ("دعم قوي — منطقة شراء جيدة ⭐⭐", "#58a6ff"),
                "61.8%": ("دعم ذهبي — منطقة شراء ممتازة ⭐⭐⭐", "#3fb950"),
                "100%":  ("قاع الموجة — شراء مخاطرة عالية", "#bc8cff"),
            }

            for level, val in fibs.items():
                diff = (val - curr_p) / curr_p * 100
                zone_desc, zone_color = fib_zones.get(level, ("—", "#8b949e"))
                is_current = abs(diff) < 2  # السعر قريب من هذا المستوى
                border_style = f"border:2px solid {zone_color}" if is_current else f"border:1px solid #30363d"
                bg_style = f"background:rgba(88,166,255,0.1)" if is_current else "background:#161b22"

                st.markdown(f"""
                <div style="display:flex;justify-content:space-between;align-items:center;
                     padding:.7rem 1rem;{bg_style};border-radius:10px;margin-bottom:.5rem;{border_style}">
                  <div>
                    <span style="color:#8b949e;font-size:.85rem">Fib {level}</span>
                    {"<span style=\'background:#58a6ff;color:#000;border-radius:4px;padding:1px 6px;font-size:.7rem;margin-right:.4rem\'>الحالي</span>" if is_current else ""}
                  </div>
                  <div style="text-align:center;flex:1;padding:0 1rem">
                    <span style="color:#8b949e;font-size:.8rem">{zone_desc}</span>
                  </div>
                  <div style="text-align:left">
                    <span style="color:{zone_color};font-weight:700;font-size:1.05rem">{val:.3f}</span>
                    <span style="color:{zone_color};font-size:.85rem;margin-right:.5rem"> ({diff:+.1f}%)</span>
                  </div>
                </div>""", unsafe_allow_html=True)

            # ملخص تحليل فيبوناتشي
            st.markdown("<br>", unsafe_allow_html=True)
            closest_support = None
            closest_resist  = None
            for level, val in fibs.items():
                if val < curr_p and (closest_support is None or val > closest_support):
                    closest_support = val
                if val > curr_p and (closest_resist is None or val < closest_resist):
                    closest_resist = val

            if closest_support or closest_resist:
                st.markdown(f"""
                <div class="ai-box">
                  <strong>📊 ملخص فيبوناتشي:</strong><br>
                  {'أقرب دعم فيبوناتشي: <strong style="color:#3fb950">' + f"{closest_support:.3f}" + '</strong> — ' + f"({(closest_support-curr_p)/curr_p*100:+.1f}%)" if closest_support else ""}
                  {"<br>" if closest_support and closest_resist else ""}
                  {'أقرب مقاومة فيبوناتشي: <strong style="color:#f85149">' + f"{closest_resist:.3f}" + '</strong> — ' + f"({(closest_resist-curr_p)/curr_p*100:+.1f}%)" if closest_resist else ""}
                </div>""", unsafe_allow_html=True)

        # حفظ في السجل
        if 'history' not in st.session_state:
            st.session_state.history = []
        st.session_state.history.append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "symbol": symbol, "price": price, "score": score,
            "verdict": verdict[0], "market": market_label.split('(')[0].strip()
        })
        if len(st.session_state.history) > 20:
            st.session_state.history = st.session_state.history[-20:]

# ── مقارنة ────────────────────────────────────────────
elif nav == "⚖️ مقارنة":
    st.markdown("### ⚖️ مقارنة سهمين")
    c1, c2 = st.columns(2)
    with c1:
        sym1 = st.text_input("السهم الأول", "2222").strip().upper()
        mkt1 = st.selectbox("السوق 1", list(MARKETS.keys()), key="m1")
    with c2:
        sym2 = st.text_input("السهم الثاني", "1120").strip().upper()
        mkt2 = st.selectbox("السوق 2", list(MARKETS.keys()), key="m2")

    if st.button("⚖️ مقارنة الآن", use_container_width=True):
        with st.spinner("جاري تحليل السهمين..."):
            d1 = get_stock_data(sym1, MARKETS[mkt1])
            d2 = get_stock_data(sym2, MARKETS[mkt2])

        for sym, data, mkt in [(sym1,d1,mkt1),(sym2,d2,mkt2)]:
            if data['error']:
                st.error(f"❌ {sym}: {data['error']}")
                continue
            tech_tmp = analyze_technicals(data['hist'])
            sigs_tmp, score_tmp, verdict_tmp, tgt_tmp = generate_signals(data['hist'], tech_tmp)
            price_tmp = data['price'] or float(data['hist']['Close'].iloc[-1])
            st.markdown(f"""
            <div class="card">
              <h3>{sym} — {mkt.split('(')[0].strip()}</h3>
              <p>السعر: <strong>{price_tmp:.3f}</strong> | الدرجة: <strong>{score_tmp}/100</strong> |
              التوصية: <strong style="color:{'#3fb950' if 'شراء' in verdict_tmp[0] else '#f85149'}">{verdict_tmp[0]}</strong></p>
            </div>""", unsafe_allow_html=True)

# ── المحفظة ───────────────────────────────────────────
elif nav == "💼 المحفظة":
    st.markdown("### 💼 المحفظة الاستثمارية")
    if 'portfolio' not in st.session_state:
        st.session_state.portfolio = []

    with st.form("add_portfolio"):
        pc1,pc2,pc3,pc4 = st.columns(4)
        with pc1: p_sym = st.text_input("رمز السهم").strip().upper()
        with pc2: p_mkt = st.selectbox("السوق", list(MARKETS.keys()), key="pmkt")
        with pc3: p_qty = st.number_input("الكمية", min_value=1, value=100)
        with pc4: p_cost = st.number_input("متوسط التكلفة", min_value=0.0, value=0.0, step=0.01)
        if st.form_submit_button("➕ إضافة للمحفظة"):
            if p_sym:
                st.session_state.portfolio.append({
                    "symbol": p_sym, "market": MARKETS[p_mkt],
                    "qty": p_qty, "cost": p_cost,
                    "added": datetime.now().strftime("%Y-%m-%d")
                })
                st.success(f"✅ تمت إضافة {p_sym}")

    if st.session_state.portfolio:
        st.markdown("---")
        total_value = 0
        total_cost  = 0
        for i, pos in enumerate(st.session_state.portfolio):
            data_p = get_stock_data(pos['symbol'], pos['market'])
            if not data_p['error']:
                curr_p = data_p['price'] or float(data_p['hist']['Close'].iloc[-1])
                value  = curr_p * pos['qty']
                cost_t = pos['cost'] * pos['qty']
                pnl    = value - cost_t
                pnl_pct= (pnl / cost_t * 100) if cost_t else 0
                total_value += value
                total_cost  += cost_t
                color = '#3fb950' if pnl >= 0 else '#f85149'
                st.markdown(f"""
                <div class="portfolio-card">
                  <div style="display:flex;justify-content:space-between;align-items:center">
                    <div>
                      <strong style="font-size:1.1rem">{pos['symbol']}</strong>
                      <span style="color:#8b949e;margin-right:.5rem;font-size:.85rem"> {pos['qty']} وحدة @ {pos['cost']:.3f}</span>
                    </div>
                    <div style="text-align:left">
                      <div>القيمة: <strong>{value:,.2f}</strong></div>
                      <div style="color:{color}">الربح/الخسارة: {pnl:+,.2f} ({pnl_pct:+.1f}%)</div>
                    </div>
                  </div>
                </div>""", unsafe_allow_html=True)
            if st.button(f"🗑️ حذف {pos['symbol']}", key=f"del_{i}"):
                st.session_state.portfolio.pop(i)
                st.rerun()

        if total_cost > 0:
            total_pnl = total_value - total_cost
            total_pct = total_pnl / total_cost * 100
            color_t = '#3fb950' if total_pnl >= 0 else '#f85149'
            st.markdown(f"""
            <div class="card" style="border-color:#58a6ff;margin-top:1rem">
              <h3>📊 ملخص المحفظة</h3>
              <p>إجمالي القيمة: <strong>{total_value:,.2f}</strong> |
              إجمالي الربح/الخسارة: <strong style="color:{color_t}">{total_pnl:+,.2f} ({total_pct:+.1f}%)</strong></p>
            </div>""", unsafe_allow_html=True)
    else:
        st.info("💡 أضف أسهمك للمحفظة لمتابعة أداءها.")

# ── التنبيهات ─────────────────────────────────────────
elif nav == "🔔 التنبيهات":
    st.markdown("### 🔔 تنبيهات الأسعار")
    if 'alerts' not in st.session_state:
        st.session_state.alerts = []

    with st.form("add_alert"):
        ac1,ac2,ac3,ac4 = st.columns(4)
        with ac1: a_sym  = st.text_input("رمز السهم").strip().upper()
        with ac2: a_mkt  = st.selectbox("السوق", list(MARKETS.keys()), key="amkt")
        with ac3: a_type = st.selectbox("نوع التنبيه", ["أعلى من", "أقل من"])
        with ac4: a_price= st.number_input("السعر المستهدف", min_value=0.0, step=0.01)
        if st.form_submit_button("➕ إضافة تنبيه"):
            if a_sym and a_price > 0:
                st.session_state.alerts.append({
                    "symbol": a_sym, "market": MARKETS[a_mkt],
                    "type": a_type, "price": a_price,
                    "created": datetime.now().strftime("%Y-%m-%d %H:%M")
                })
                st.success(f"✅ تم إضافة التنبيه: {a_sym} {a_type} {a_price}")

    if st.session_state.alerts:
        st.markdown("---")
        for i, alert in enumerate(st.session_state.alerts):
            data_a = get_stock_data(alert['symbol'], alert['market'])
            curr_a = None
            if not data_a['error']:
                curr_a = data_a['price'] or float(data_a['hist']['Close'].iloc[-1])
                triggered = (alert['type'] == "أعلى من" and curr_a >= alert['price']) or \
                            (alert['type'] == "أقل من"  and curr_a <= alert['price'])
                border = '#3fb950' if triggered else '#30363d'
                status = "🔔 مُفعَّل!" if triggered else "⏳ منتظر"
                st.markdown(f"""
                <div class="alert-card" style="border-color:{border}">
                  <div style="display:flex;justify-content:space-between">
                    <div><strong>{alert['symbol']}</strong> | {alert['type']} {alert['price']:.3f}</div>
                    <div>الحالي: {curr_a:.3f} | {status}</div>
                  </div>
                </div>""", unsafe_allow_html=True)
            if st.button(f"🗑️ حذف التنبيه {i+1}", key=f"del_a_{i}"):
                st.session_state.alerts.pop(i)
                st.rerun()
    else:
        st.info("💡 أضف تنبيهات لمتابعة أسعار الأسهم.")

# ── المراقبة ──────────────────────────────────────────
elif nav == "👁️ المراقبة":
    st.markdown("### 👁️ قائمة المراقبة")
    if 'watchlist' not in st.session_state:
        st.session_state.watchlist = [("2222","sa"),("1120","sa"),("AAPL","us"),("NVDA","us")]

    if st.button("🔄 تحديث الكل"):
        st.rerun()

    if st.session_state.watchlist:
        for sym, mkt in st.session_state.watchlist:
            data_w = get_stock_data(sym, mkt)
            if not data_w['error']:
                tech_w = analyze_technicals(data_w['hist'])
                _, score_w, verdict_w, _ = generate_signals(data_w['hist'], tech_w)
                price_w = data_w['price'] or float(data_w['hist']['Close'].iloc[-1])
                prev_w  = float(data_w['hist']['Close'].iloc[-2]) if len(data_w['hist']) > 1 else price_w
                chg_w   = price_w - prev_w
                chg_p_w = (chg_w / prev_w * 100) if prev_w else 0
                color_w = '#3fb950' if chg_w >= 0 else '#f85149'
                st.markdown(f"""
                <div class="card" style="margin-bottom:.5rem">
                  <div style="display:flex;justify-content:space-between;align-items:center">
                    <div>
                      <strong style="font-size:1.1rem">{sym}</strong>
                      <span class="badge {'b-green' if score_w>=60 else 'b-red' if score_w<40 else 'b-yellow'}" style="margin-right:.4rem">
                        {verdict_w[0]}
                      </span>
                    </div>
                    <div style="text-align:left">
                      <strong>{price_w:.3f}</strong>
                      <span style="color:{color_w};margin-right:.5rem"> ({chg_p_w:+.1f}%)</span>
                    </div>
                  </div>
                </div>""", unsafe_allow_html=True)
    else:
        st.info("أضف أسهماً للمراقبة من صفحة التحليل.")

# ── السجل ─────────────────────────────────────────────
elif nav == "📜 السجل":
    st.markdown("### 📜 سجل التحليلات")
    history = st.session_state.get('history', [])
    if history:
        for h in reversed(history[-20:]):
            color = '#3fb950' if 'شراء' in h['verdict'] else '#f85149' if 'بيع' in h['verdict'] else '#d29922'
            st.markdown(f"""
            <div class="card" style="margin-bottom:.4rem">
              <div style="display:flex;justify-content:space-between">
                <span><strong>{h['symbol']}</strong> | {h['market']}</span>
                <span>السعر: {h['price']:.3f} | الدرجة: {h['score']}/100 |
                  <strong style="color:{color}">{h['verdict']}</strong></span>
                <span style="color:#8b949e;font-size:.8rem">{h['time']}</span>
              </div>
            </div>""", unsafe_allow_html=True)
        if st.button("🗑️ مسح السجل"):
            st.session_state.history = []
            st.rerun()
    else:
        st.info("لا يوجد سجل بعد. ابدأ بتحليل سهم.")
