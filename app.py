import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import warnings, io, json, time, requests
warnings.filterwarnings('ignore')

st.set_page_config(page_title="محلل الأسهم الذكي Pro v3",page_icon="📈",layout="wide",initial_sidebar_state="collapsed")

# ── CSS (محتفظ به كما هو) ────────────────────────────────────────────────────
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
.tab-content{padding:.5rem 0;}
.stTabs [data-baseweb="tab"]{font-family:'Cairo',sans-serif;font-size:.88rem;}
.stButton>button{border-radius:10px;font-family:'Cairo',sans-serif;font-weight:700;}
</style>
""", unsafe_allow_html=True)

# ── مصدر البيانات: Stooq + yfinance fallback ─────────────────────────────────

def to_stooq_symbol(symbol: str, market: str) -> str:
    s = symbol.upper().strip()
    if market in ("sa", "saudi", "tasi"):
        if s.isdigit():
            return f"{s}.sr"
        if not s.endswith(".sr"):
            return f"{s}.sr"
        return s.lower()
    return f"{s}.us"

def fetch_stooq(symbol: str, market: str) -> pd.DataFrame:
    """جلب البيانات التاريخية من Stooq"""
    stooq_sym = to_stooq_symbol(symbol, market)
    url = f"https://stooq.com/q/d/l/?s={stooq_sym}&i=d"
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200 or "No data" in r.text or len(r.text) < 50:
            return pd.DataFrame()
        from io import StringIO
        df = pd.read_csv(StringIO(r.text))
        df.columns = [c.lower() for c in df.columns]
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').tail(365)
        df = df.rename(columns={"open":"Open","high":"High","low":"Low","close":"Close","volume":"Volume"})
        df.index = df['date']
        return df[['Open','High','Low','Close','Volume']].dropna()
    except Exception as e:
        return pd.DataFrame()

def fetch_yfinance(symbol: str, market: str) -> tuple:
    """جلب البيانات من yfinance كـ Fallback"""
    try:
        import yfinance as yf
        if market in ("sa", "saudi", "tasi"):
            yf_sym = f"{symbol}.SR" if not symbol.endswith(".SR") else symbol
        else:
            yf_sym = symbol.upper()
        
        ticker = yf.Ticker(yf_sym)
        hist = ticker.history(period="1y")
        info = {}
        try:
            info = ticker.info or {}
        except Exception:
            pass
        return hist, info
    except Exception:
        return pd.DataFrame(), {}

def get_stock_data(symbol: str, market: str) -> dict:
    """جلب بيانات السهم — Stooq أولاً ثم yfinance"""
    result = {
        "hist": pd.DataFrame(),
        "info": {},
        "price": None,
        "source": "none",
        "error": None
    }
    
    # محاولة Stooq أولاً
    hist_stooq = fetch_stooq(symbol, market)
    
    if not hist_stooq.empty and len(hist_stooq) >= 10:
        result["hist"] = hist_stooq
        result["price"] = float(hist_stooq['Close'].iloc[-1])
        result["source"] = "stooq"
    
    # محاولة yfinance للأسعار الحية والمعلومات الإضافية
    try:
        hist_yf, info_yf = fetch_yfinance(symbol, market)
        if not hist_yf.empty:
            if result["hist"].empty:
                result["hist"] = hist_yf
                result["source"] = "yfinance"
            # استخدم yfinance للسعر الحي فقط إذا كان متاحاً
            live_price = info_yf.get("regularMarketPrice") or info_yf.get("currentPrice")
            if live_price:
                result["price"] = live_price
                result["source"] = "stooq+yfinance" if result["source"] == "stooq" else "yfinance"
        if info_yf:
            result["info"] = info_yf
    except Exception:
        pass
    
    if result["hist"].empty:
        result["error"] = f"لم يُعثر على بيانات للرمز '{symbol}'. تأكد من صحة الرمز والسوق."
    
    return result

# ── الحسابات الفنية ───────────────────────────────────────────────────────────

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
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def calculate_stochastic(high, low, close, k=14, d=3):
    low_k = low.rolling(k).min()
    high_k = high.rolling(k).max()
    stoch_k = 100 * (close - low_k) / (high_k - low_k + 1e-9)
    stoch_d = stoch_k.rolling(d).mean()
    return stoch_k, stoch_d

def detect_support_resistance(df, n=20):
    highs = df['High'].rolling(n, center=True).max()
    lows = df['Low'].rolling(n, center=True).min()
    resistance = highs.dropna().unique()[-3:] if len(highs.dropna()) >= 3 else []
    support = lows.dropna().unique()[:3] if len(lows.dropna()) >= 3 else []
    return sorted(resistance, reverse=True)[:3], sorted(support)[:3]

def analyze_technicals(df):
    close = df['Close']
    high = df['High']
    low = df['Low']
    volume = df['Volume']
    
    rsi = calculate_rsi(close)
    macd, macd_sig, macd_hist = calculate_macd(close)
    bb_upper, bb_mid, bb_lower = calculate_bollinger(close)
    atr = calculate_atr(high, low, close)
    stoch_k, stoch_d = calculate_stochastic(high, low, close)
    
    sma20 = close.rolling(20).mean()
    sma50 = close.rolling(50).mean()
    sma200 = close.rolling(200).mean()
    ema12 = close.ewm(span=12).mean()
    ema26 = close.ewm(span=26).mean()
    
    resistance, support = detect_support_resistance(df)
    
    return {
        "rsi": rsi, "macd": macd, "macd_sig": macd_sig, "macd_hist": macd_hist,
        "bb_upper": bb_upper, "bb_mid": bb_mid, "bb_lower": bb_lower,
        "atr": atr, "stoch_k": stoch_k, "stoch_d": stoch_d,
        "sma20": sma20, "sma50": sma50, "sma200": sma200,
        "ema12": ema12, "ema26": ema26,
        "resistance": resistance, "support": support,
        "volume": volume
    }

def generate_signals(df, tech):
    close = df['Close']
    curr = close.iloc[-1]
    
    signals = {}
    score = 50
    
    # RSI
    rsi_v = tech['rsi'].iloc[-1]
    if not np.isnan(rsi_v):
        if rsi_v < 30: signals['RSI'] = ('شراء قوي', 'b-green', +15)
        elif rsi_v < 45: signals['RSI'] = ('شراء', 'b-green', +8)
        elif rsi_v > 70: signals['RSI'] = ('بيع قوي', 'b-red', -15)
        elif rsi_v > 55: signals['RSI'] = ('بيع', 'b-red', -8)
        else: signals['RSI'] = ('محايد', 'b-yellow', 0)
    
    # MACD
    mh = tech['macd_hist'].iloc[-1]
    mp = tech['macd_hist'].iloc[-2] if len(tech['macd_hist']) > 1 else mh
    if not np.isnan(mh):
        if mh > 0 and mh > mp: signals['MACD'] = ('شراء قوي', 'b-green', +12)
        elif mh > 0: signals['MACD'] = ('شراء', 'b-green', +6)
        elif mh < 0 and mh < mp: signals['MACD'] = ('بيع قوي', 'b-red', -12)
        else: signals['MACD'] = ('بيع', 'b-red', -6)
    
    # Bollinger
    bbu = tech['bb_upper'].iloc[-1]
    bbl = tech['bb_lower'].iloc[-1]
    if not np.isnan(bbu):
        if curr < bbl: signals['بولينجر'] = ('تشبع بيعي - شراء', 'b-green', +10)
        elif curr > bbu: signals['بولينجر'] = ('تشبع شرائي - بيع', 'b-red', -10)
        else: signals['بولينجر'] = ('ضمن النطاق', 'b-yellow', 0)
    
    # المتوسطات
    sma20_v = tech['sma20'].iloc[-1]
    sma50_v = tech['sma50'].iloc[-1]
    if not np.isnan(sma20_v) and not np.isnan(sma50_v):
        if curr > sma20_v and curr > sma50_v:
            signals['المتوسطات'] = ('فوق SMA20 و50 - صاعد', 'b-green', +10)
        elif curr < sma20_v and curr < sma50_v:
            signals['المتوسطات'] = ('تحت SMA20 و50 - هابط', 'b-red', -10)
        else:
            signals['المتوسطات'] = ('مختلط', 'b-yellow', 0)
    
    # Stochastic
    sk = tech['stoch_k'].iloc[-1]
    if not np.isnan(sk):
        if sk < 20: signals['ستوكاستك'] = ('تشبع بيعي', 'b-green', +8)
        elif sk > 80: signals['ستوكاستك'] = ('تشبع شرائي', 'b-red', -8)
        else: signals['ستوكاستك'] = ('محايد', 'b-yellow', 0)
    
    for sig in signals.values():
        score += sig[2]
    score = max(5, min(95, score))
    
    if score >= 75: verdict = ('شراء قوي', 'v-strong-buy', '#3fb950')
    elif score >= 60: verdict = ('شراء', 'v-buy', '#58a6ff')
    elif score >= 45: verdict = ('احتفاظ', 'v-hold', '#d29922')
    elif score >= 30: verdict = ('تخفيض', 'v-reduce', '#f0883e')
    else: verdict = ('بيع', 'v-sell', '#f85149')
    
    return signals, score, verdict

# ── الرسم البياني ─────────────────────────────────────────────────────────────

def build_chart(df, tech, symbol):
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.60, 0.20, 0.20],
        subplot_titles=("", "RSI", "MACD")
    )
    
    # شموع يابانية
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'],
        low=df['Low'], close=df['Close'], name="السعر",
        increasing=dict(line=dict(color='#3fb950'), fillcolor='#3fb950'),
        decreasing=dict(line=dict(color='#f85149'), fillcolor='#f85149'),
    ), row=1, col=1)
    
    # المتوسطات
    if not tech['sma20'].isna().all():
        fig.add_trace(go.Scatter(x=df.index, y=tech['sma20'], name='SMA20',
            line=dict(color='#58a6ff', width=1.5)), row=1, col=1)
    if not tech['sma50'].isna().all():
        fig.add_trace(go.Scatter(x=df.index, y=tech['sma50'], name='SMA50',
            line=dict(color='#d29922', width=1.5)), row=1, col=1)
    
    # بولينجر
    if not tech['bb_upper'].isna().all():
        fig.add_trace(go.Scatter(x=df.index, y=tech['bb_upper'], name='BB↑',
            line=dict(color='#bc8cff', width=1, dash='dash')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=tech['bb_lower'], name='BB↓',
            line=dict(color='#bc8cff', width=1, dash='dash'),
            fill='tonexty', fillcolor='rgba(188,140,255,0.05)'), row=1, col=1)
    
    # RSI
    fig.add_trace(go.Scatter(x=df.index, y=tech['rsi'], name='RSI',
        line=dict(color='#58a6ff', width=2)), row=2, col=1)
    fig.add_hline(y=70, line=dict(color='#f85149', width=1, dash='dot'), row=2, col=1)
    fig.add_hline(y=30, line=dict(color='#3fb950', width=1, dash='dot'), row=2, col=1)
    fig.add_hrect(y0=70, y1=100, fillcolor='rgba(248,81,73,0.07)', line_width=0, row=2, col=1)
    fig.add_hrect(y0=0, y1=30, fillcolor='rgba(63,185,80,0.07)', line_width=0, row=2, col=1)
    
    # MACD
    colors = ['#3fb950' if v >= 0 else '#f85149' for v in tech['macd_hist'].fillna(0)]
    fig.add_trace(go.Bar(x=df.index, y=tech['macd_hist'], name='MACD Hist',
        marker_color=colors, opacity=0.7), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=tech['macd'], name='MACD',
        line=dict(color='#58a6ff', width=1.5)), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=tech['macd_sig'], name='Signal',
        line=dict(color='#f0883e', width=1.5)), row=3, col=1)
    
    fig.update_layout(
        paper_bgcolor='#0d1117', plot_bgcolor='#0d1117',
        font=dict(color='#e6edf3', family='Cairo'),
        height=680, margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation='h', y=1.05, x=0,
            bgcolor='rgba(22,27,34,0.8)', bordercolor='#30363d', borderwidth=1),
        xaxis_rangeslider_visible=False,
        hovermode='x unified',
    )
    for ax in ['xaxis', 'xaxis2', 'xaxis3', 'yaxis', 'yaxis2', 'yaxis3']:
        fig.update_layout(**{ax: dict(gridcolor='#21262d', gridwidth=0.5,
            showgrid=True, zeroline=False)})
    fig.update_layout(yaxis2=dict(range=[0, 100]))
    
    return fig

# ── الواجهة الرئيسية ──────────────────────────────────────────────────────────

st.markdown("""
<div class="pro-header">
  <h1>📊 محلل الأسهم الذكي Pro v3</h1>
  <p>محفظة • تنبيهات • أخبار • AI •• تحليل شامل • 10 أسواق عالمية • بيانات لحظية</p>
</div>
""", unsafe_allow_html=True)

# أزرار التنقل
nav = st.radio("", ["🔍 تحليل", "⚖️ مقارنة", "💼 المحفظة", "🔔 التنبيهات", "👁️ المراقبة", "📜 السجل"],
    horizontal=True, label_visibility="collapsed")

st.divider()

# ── صفحة التحليل ─────────────────────────────────────────────────────────────
if nav == "🔍 تحليل":
    
    col_sym, col_mkt, col_btn = st.columns([3, 2, 1])
    
    MARKETS = {
        "🇸🇦 السوق السعودي (TASI)": "sa",
        "🇺🇸 الأمريكي (NYSE/NASDAQ)": "us",
        "🇦🇪 الإماراتي (DFM/ADX)": "ae",
        "🇶🇦 القطري (QE)": "qa",
        "🇰🇼 الكويتي (BK)": "kw",
        "🇧🇭 البحريني": "bh",
        "🇯🇴 الأردني": "jo",
        "🇪🇬 المصري (EGX)": "eg",
        "🇬🇧 البريطاني (LSE)": "gb",
        "🇩🇪 الألماني (XETRA)": "de",
    }
    
    with col_sym:
        symbol = st.text_input("🔍 رمز السهم", placeholder="مثال: 2222 أو AAPL", label_visibility="collapsed").strip().upper()
    with col_mkt:
        market_label = st.selectbox("السوق", list(MARKETS.keys()), label_visibility="collapsed")
        market = MARKETS[market_label]
    with col_btn:
        analyze = st.button("📊 تحليل السهم", use_container_width=True)
    
    # أسهم سريعة
    st.markdown("**⚡ أسهم سريعة:**")
    quick_cols = st.columns(8)
    quick_stocks = [("2222","sa"),("1120","sa"),("7010","sa"),("2010","sa"),
                    ("AAPL","us"),("NVDA","us"),("TSLA","us"),("MSFT","us")]
    for i, (sym, mkt) in enumerate(quick_stocks):
        with quick_cols[i]:
            if st.button(sym, key=f"q_{sym}"):
                st.session_state['q_sym'] = sym
                st.session_state['q_mkt'] = mkt
                st.rerun()
    
    if 'q_sym' in st.session_state:
        symbol = st.session_state.pop('q_sym')
        market = st.session_state.pop('q_mkt', 'sa')
        analyze = True
    
    if analyze and symbol:
        with st.spinner(f"⏳ جاري جلب بيانات {symbol}..."):
            data = get_stock_data(symbol, market)
        
        if data['error']:
            st.error(f"❌ {data['error']}")
            st.stop()
        
        df = data['hist']
        info = data['info']
        price = data['price'] or df['Close'].iloc[-1]
        source = data['source']
        
        # حساب التغيير
        prev_close = df['Close'].iloc[-2] if len(df) > 1 else price
        change = price - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0
        
        # التحليل الفني
        tech = analyze_technicals(df)
        signals, score, verdict = generate_signals(df, tech)
        
        # معلومات السهم
        name = info.get('longName') or info.get('shortName') or symbol
        currency = info.get('currency', 'SAR' if market == 'sa' else 'USD')
        
        st.markdown(f"""
        <div class="card" style="margin-bottom:1rem">
          <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:1rem">
            <div>
              <div style="font-size:1.3rem;font-weight:900">{name}</div>
              <div style="color:#8b949e;font-size:.85rem">{symbol} · {market_label.split('(')[0].strip()}</div>
              <span class="badge b-blue" style="margin-top:.3rem">المصدر: {source}</span>
            </div>
            <div style="text-align:left">
              <div style="font-size:2.2rem;font-weight:900">{price:.3f} <span style="font-size:1rem;color:#8b949e">{currency}</span></div>
              <div style="color:{'#3fb950' if change >= 0 else '#f85149'};font-size:1rem;font-weight:700">
                {'▲' if change >= 0 else '▼'} {abs(change):.3f} ({change_pct:+.2f}%)
              </div>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)
        
        # مؤشرات رئيسية
        rsi_v = tech['rsi'].iloc[-1]
        atr_v = tech['atr'].iloc[-1]
        vol_v = df['Volume'].iloc[-1]
        vol_avg = df['Volume'].rolling(20).mean().iloc[-1]
        
        c1,c2,c3,c4,c5,c6 = st.columns(6)
        metrics = [
            (c1, "الدرجة الكلية", f"{score}/100", '#3fb950' if score>=60 else '#f85149'),
            (c2, "RSI(14)", f"{rsi_v:.1f}" if not np.isnan(rsi_v) else "—",
             '#3fb950' if rsi_v<30 else '#f85149' if rsi_v>70 else '#58a6ff'),
            (c3, "ATR(14)", f"{atr_v:.3f}" if not np.isnan(atr_v) else "—", '#8b949e'),
            (c4, "BB العلوي", f"{tech['bb_upper'].iloc[-1]:.3f}" if not tech['bb_upper'].isna().all() else "—", '#bc8cff'),
            (c5, "BB السفلي", f"{tech['bb_lower'].iloc[-1]:.3f}" if not tech['bb_lower'].isna().all() else "—", '#bc8cff'),
            (c6, "حجم التداول", f"{vol_v/1e6:.1f}M" if vol_v >= 1e6 else str(int(vol_v)), '#8b949e'),
        ]
        for col, lbl, val, color in metrics:
            with col:
                st.markdown(f"""
                <div class="metric-card">
                  <div class="metric-val" style="color:{color}">{val}</div>
                  <div class="metric-lbl">{lbl}</div>
                </div>""", unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # التبويبات
        tab1, tab2, tab3, tab4 = st.tabs(["📈 الرسم البياني", "🎯 التوصية والإشارات", "📊 التحليل الفني", "ℹ️ معلومات السهم"])
        
        with tab1:
            fig = build_chart(df, tech, symbol)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": True, "displaylogo": False})
        
        with tab2:
            # التوصية
            st.markdown(f"""
            <div class="verdict-box {verdict[1]}">
              <div class="verdict-title" style="color:{verdict[2]}">{verdict[0]}</div>
              <div class="verdict-sub">درجة الثقة: {score}/100</div>
            </div>
            """, unsafe_allow_html=True)
            
            # الإشارات
            st.markdown("### 📡 الإشارات التفصيلية")
            sig_cols = st.columns(len(signals))
            for i, (k, v) in enumerate(signals.items()):
                with sig_cols[i]:
                    st.markdown(f"""
                    <div class="metric-card" style="text-align:center">
                      <div style="font-size:.8rem;color:#8b949e;margin-bottom:.3rem">{k}</div>
                      <span class="badge {v[1]}">{v[0]}</span>
                    </div>""", unsafe_allow_html=True)
            
            # الدعم والمقاومة
            st.markdown("### 🎯 الدعم والمقاومة")
            sr_c1, sr_c2 = st.columns(2)
            with sr_c1:
                st.markdown("**🔴 المقاومة**")
                for r in tech['resistance']:
                    if not np.isnan(r):
                        diff = ((r - price) / price * 100)
                        st.markdown(f"`{r:.3f}` — ({diff:+.1f}%)")
            with sr_c2:
                st.markdown("**🟢 الدعم**")
                for s in tech['support']:
                    if not np.isnan(s):
                        diff = ((s - price) / price * 100)
                        st.markdown(f"`{s:.3f}` — ({diff:+.1f}%)")
        
        with tab3:
            c1, c2 = st.columns(2)
            
            ind_data = [
                ("RSI(14)", f"{tech['rsi'].iloc[-1]:.1f}" if not np.isnan(tech['rsi'].iloc[-1]) else "—"),
                ("MACD", f"{tech['macd'].iloc[-1]:.4f}" if not np.isnan(tech['macd'].iloc[-1]) else "—"),
                ("MACD Signal", f"{tech['macd_sig'].iloc[-1]:.4f}" if not np.isnan(tech['macd_sig'].iloc[-1]) else "—"),
                ("Stoch K", f"{tech['stoch_k'].iloc[-1]:.1f}" if not np.isnan(tech['stoch_k'].iloc[-1]) else "—"),
                ("SMA(20)", f"{tech['sma20'].iloc[-1]:.3f}" if not np.isnan(tech['sma20'].iloc[-1]) else "—"),
                ("SMA(50)", f"{tech['sma50'].iloc[-1]:.3f}" if not np.isnan(tech['sma50'].iloc[-1]) else "—"),
                ("BB Upper", f"{tech['bb_upper'].iloc[-1]:.3f}" if not np.isnan(tech['bb_upper'].iloc[-1]) else "—"),
                ("BB Lower", f"{tech['bb_lower'].iloc[-1]:.3f}" if not np.isnan(tech['bb_lower'].iloc[-1]) else "—"),
                ("ATR(14)", f"{tech['atr'].iloc[-1]:.3f}" if not np.isnan(tech['atr'].iloc[-1]) else "—"),
            ]
            
            with c1:
                for lbl, val in ind_data[:5]:
                    st.markdown(f"**{lbl}:** `{val}`")
            with c2:
                for lbl, val in ind_data[5:]:
                    st.markdown(f"**{lbl}:** `{val}`")
        
        with tab4:
            if info:
                fields = [
                    ("الاسم الكامل", info.get('longName', '—')),
                    ("القطاع", info.get('sector', '—')),
                    ("الصناعة", info.get('industry', '—')),
                    ("البورصة", info.get('exchange', '—')),
                    ("العملة", info.get('currency', '—')),
                    ("القيمة السوقية", f"{info.get('marketCap', 0)/1e9:.1f}B" if info.get('marketCap') else '—'),
                    ("P/E", f"{info.get('trailingPE', '—'):.2f}" if isinstance(info.get('trailingPE'), float) else '—'),
                    ("EPS", f"{info.get('trailingEps', '—'):.3f}" if isinstance(info.get('trailingEps'), float) else '—'),
                    ("عائد التوزيعات", f"{info.get('dividendYield', 0)*100:.2f}%" if info.get('dividendYield') else '—'),
                    ("52 أسبوع أعلى", f"{info.get('fiftyTwoWeekHigh', '—'):.3f}" if isinstance(info.get('fiftyTwoWeekHigh'), float) else '—'),
                    ("52 أسبوع أدنى", f"{info.get('fiftyTwoWeekLow', '—'):.3f}" if isinstance(info.get('fiftyTwoWeekLow'), float) else '—'),
                ]
                for lbl, val in fields:
                    col_a, col_b = st.columns([1, 2])
                    with col_a: st.markdown(f"**{lbl}**")
                    with col_b: st.markdown(f"`{val}`")
                
                desc = info.get('longBusinessSummary', '')
                if desc:
                    with st.expander("📝 نبذة عن الشركة"):
                        st.write(desc[:500] + "..." if len(desc) > 500 else desc)
            else:
                st.info("ℹ️ المعلومات التفصيلية غير متاحة من Stooq. جرب سهماً أمريكياً للحصول على معلومات كاملة.")

elif nav == "⚖️ مقارنة":
    st.info("🔧 ميزة المقارنة قيد التطوير")

elif nav == "💼 المحفظة":
    st.info("🔧 ميزة المحفظة قيد التطوير")

elif nav == "🔔 التنبيهات":
    st.info("🔧 ميزة التنبيهات قيد التطوير")

elif nav == "👁️ المراقبة":
    st.info("🔧 ميزة المراقبة قيد التطوير")

elif nav == "📜 السجل":
    st.info("🔧 السجل قيد التطوير")
