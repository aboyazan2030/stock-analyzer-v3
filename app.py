import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import warnings, io, json, time
warnings.filterwarnings('ignore')

# ── Page Config ───────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="محلل الأسهم الذكي Pro v3",
    page_icon="📈", layout="wide",
    initial_sidebar_state="collapsed"
)

# ── CSS ───────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap');
*{box-sizing:border-box;}
html,body,[class*="css"]{font-family:'Cairo',sans-serif;background:#0d1117;color:#e6edf3;}
.stApp{background:#0d1117;}
.block-container{padding:1rem 1.5rem 3rem;}

.pro-header{background:linear-gradient(135deg,#0d1117,#161b22);
  border-bottom:1px solid #30363d;padding:1.4rem;text-align:center;
  border-radius:0 0 16px 16px;margin-bottom:1.2rem;}
.pro-header h1{font-size:1.9rem;font-weight:900;
  background:linear-gradient(90deg,#58a6ff,#bc8cff,#3fb950);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;}
.pro-header p{color:#8b949e;font-size:.85rem;margin-top:.2rem;}

.card{background:#161b22;border:1px solid #30363d;border-radius:12px;
  padding:1.1rem;margin-bottom:.7rem;}
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

.pro-table{width:100%;border-collapse:collapse;font-size:.86rem;}
.pro-table th{background:#21262d;color:#8b949e;font-weight:700;
  padding:.6rem .9rem;text-align:right;border-bottom:1px solid #30363d;}
.pro-table td{padding:.6rem .9rem;border-bottom:1px solid #21262d;color:#e6edf3;}
.pro-table tr:hover td{background:#1c2128;}

.conf-wrap{margin:.5rem 0;}
.conf-row{display:flex;justify-content:space-between;font-size:.8rem;margin-bottom:3px;}
.conf-track{background:#21262d;border-radius:20px;height:8px;overflow:hidden;}
.conf-fill{height:100%;border-radius:20px;}

.news-item{background:#161b22;border:1px solid #30363d;border-radius:10px;
  padding:.9rem;margin-bottom:.6rem;}
.news-title{font-size:.9rem;font-weight:700;color:#e6edf3;margin-bottom:.3rem;}
.news-meta{font-size:.75rem;color:#8b949e;}
.news-sent-pos{color:#3fb950;font-weight:700;}
.news-sent-neg{color:#f85149;font-weight:700;}
.news-sent-neu{color:#d29922;font-weight:700;}

.alert-item{background:#161b22;border-left:3px solid #58a6ff;
  border-radius:0 10px 10px 0;padding:.8rem 1rem;margin-bottom:.5rem;}

.stButton>button{background:linear-gradient(135deg,#1f6feb,#388bfd);color:#fff;
  border:none;border-radius:10px;font-size:.95rem;font-weight:700;
  padding:.6rem 1.4rem;width:100%;font-family:'Cairo',sans-serif;transition:opacity .2s;}
.stButton>button:hover{opacity:.85;}
.stButton>button[kind="secondary"]{background:#21262d;border:1px solid #30363d;}

.stTextInput>div>div>input,.stSelectbox>div>div,.stNumberInput>div>div>input{
  background:#1c2128!important;border:1px solid #30363d!important;
  border-radius:8px!important;color:#e6edf3!important;font-family:'Cairo',sans-serif;}

div[data-testid="stMetric"]{background:#161b22;border:1px solid #30363d;
  border-radius:10px;padding:.7rem .9rem;}
div[data-testid="stMetricLabel"]{color:#8b949e!important;font-size:.78rem!important;}
div[data-testid="stMetricValue"]{color:#e6edf3!important;font-size:1.2rem!important;}

.section-title{font-size:1.05rem;font-weight:700;color:#e6edf3;
  border-bottom:2px solid #58a6ff;padding-bottom:.4rem;margin:1rem 0 .7rem;}

.disclaimer{background:rgba(210,153,34,.07);border:1px solid #d29922;
  border-radius:10px;padding:.7rem 1rem;font-size:.76rem;
  color:#8b949e;margin-top:1.2rem;text-align:center;}

.ai-box{background:linear-gradient(135deg,rgba(88,166,255,.08),rgba(188,140,255,.08));
  border:1px solid #58a6ff;border-radius:12px;padding:1.2rem;margin:.8rem 0;}
.ai-title{color:#58a6ff;font-weight:700;font-size:.9rem;margin-bottom:.5rem;}

footer,#MainMenu,.stDeployButton{display:none!important;}
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────────
MARKETS = {
    "🇸🇦 السوق السعودي (TASI)":       "SA",
    "🇺🇸 السوق الأمريكي (NYSE/NASDAQ)":"US",
    "🇬🇧 السوق البريطاني (LSE)":       "UK",
    "🇩🇪 السوق الألماني (XETRA)":      "DE",
    "🇯🇵 السوق الياباني (TSE)":        "JP",
    "🇭🇰 هونغ كونغ (HKEX)":           "HK",
    "🇫🇷 السوق الفرنسي (Euronext)":    "FR",
    "🇨🇦 السوق الكندي (TSX)":          "CA",
    "🇦🇺 السوق الأسترالي (ASX)":       "AU",
    "🇨🇳 السوق الصيني (Shanghai)":     "CN",
}
SUFFIX = {"SA":".SR","US":"","UK":".L","DE":".DE","JP":".T",
          "HK":".HK","FR":".PA","CA":".TO","AU":".AX","CN":".SS"}

CHART_BG = dict(
    paper_bgcolor="#0d1117", plot_bgcolor="#0d1117",
    font=dict(color="#e6edf3", family="Cairo"),
    xaxis=dict(gridcolor="#21262d", showgrid=True, zeroline=False),
    yaxis=dict(gridcolor="#21262d", showgrid=True, zeroline=False),
    margin=dict(l=8,r=8,t=36,b=8),
    legend=dict(bgcolor="rgba(0,0,0,0)")
)

# ── Session State Init ────────────────────────────────────────────────────────────
def init_state():
    if "portfolio"   not in st.session_state: st.session_state.portfolio   = []
    if "alerts"      not in st.session_state: st.session_state.alerts      = []
    if "history"     not in st.session_state: st.session_state.history     = []
    if "watchlist"   not in st.session_state: st.session_state.watchlist   = []

init_state()

# ── Helpers ───────────────────────────────────────────────────────────────────────
def safe(d, k, default=None):
    v = d.get(k, default) if isinstance(d, dict) else default
    if v is None: return default
    try:
        if isinstance(v, float) and np.isnan(v): return default
    except: pass
    return v

def fmt(n, s=""):
    if n is None: return "—"
    try:
        n=float(n)
        if np.isnan(n): return "—"
        if abs(n)>=1e12: return f"{n/1e12:.2f}T{s}"
        if abs(n)>=1e9:  return f"{n/1e9:.2f}B{s}"
        if abs(n)>=1e6:  return f"{n/1e6:.2f}M{s}"
        return f"{n:,.2f}{s}"
    except: return "—"

def pct(n):
    if n is None: return "—"
    try:
        n=float(n)
        if np.isnan(n): return "—"
        return f"{n*100:.1f}%"
    except: return "—"

def badge(text, kind="blue"):
    return f'<span class="badge b-{kind}">{text}</span>'

def sbadge(val, hi, lo):
    if val is None: return badge("—","blue")
    try:
        v=float(val)
        if v>=hi: return badge("قوي ↑","green")
        if v<=lo: return badge("ضعيف ↓","red")
        return badge("متوسط","yellow")
    except: return badge("—","blue")

def get_ticker(sym, mc):
    return f"{sym.upper()}{SUFFIX.get(mc,'')}"

# ── Data Fetch ────────────────────────────────────────────────────────────────────
def fetch_stock(ticker):
    try:
        stk  = yf.Ticker(ticker)
        info = stk.info
        hist = stk.history(period="2y", interval="1d", auto_adjust=True)
        if hist.empty: return None, None, None
        return info, hist, stk
    except Exception as e:
        return None, None, None

def fetch_news(ticker):
    try:
        stk = yf.Ticker(ticker)
        news = stk.news
        return news[:10] if news else []
    except: return []

# ── Technical ─────────────────────────────────────────────────────────────────────
def compute_tech(hist):
    df = hist.copy()
    c  = df["Close"]
    df["MA20"]  = c.rolling(20).mean()
    df["MA50"]  = c.rolling(50).mean()
    df["MA200"] = c.rolling(200).mean()
    d=c.diff(); g=d.clip(lower=0).rolling(14).mean()
    l=(-d.clip(upper=0)).rolling(14).mean()
    df["RSI"] = 100-100/(1+g/l.replace(0,np.nan))
    e12=c.ewm(span=12,adjust=False).mean()
    e26=c.ewm(span=26,adjust=False).mean()
    df["MACD"]  =e12-e26
    df["MACD_S"]=df["MACD"].ewm(span=9,adjust=False).mean()
    df["MACD_H"]=df["MACD"]-df["MACD_S"]
    df["BB_M"]=c.rolling(20).mean()
    std=c.rolling(20).std()
    df["BB_U"]=df["BB_M"]+2*std
    df["BB_L"]=df["BB_M"]-2*std
    r=df.tail(60)
    return df, float(r["Low"].min()), float(r["High"].max())

def analyze_tech(df, sup, res, price):
    last=df.iloc[-1]
    ma50 =float(last["MA50"])  if not pd.isna(last["MA50"])  else None
    ma200=float(last["MA200"]) if not pd.isna(last["MA200"]) else None
    rsi  =float(last["RSI"])   if not pd.isna(last["RSI"])   else None
    macd =float(last["MACD"]); macd_s=float(last["MACD_S"])
    bb_u =float(last["BB_U"])  if not pd.isna(last["BB_U"])  else None
    bb_l =float(last["BB_L"])  if not pd.isna(last["BB_L"])  else None
    score=0

    if ma50 and ma200:
        if price>ma50>ma200:  trend="صاعد قوي 🟢";   score+=3
        elif price>ma50:       trend="صاعد معتدل 🔵"; score+=2
        elif price<ma50<ma200: trend="هابط قوي 🔴";   score-=2
        else:                   trend="متذبذب 🟡"
    else: trend="غير محدد"

    if rsi:
        if rsi<30:   rs="تشبع بيعي — فرصة 🟢";  score+=2
        elif rsi>70: rs="تشبع شرائي — تحذير 🔴"; score-=1
        else:         rs="منطقة محايدة 🟡";        score+=1
    else: rs="—"

    ms="إيجابي 🟢"; score+=2
    if macd<=macd_s: ms="سلبي 🔴"; score-=1; ms="سلبي 🔴"
    else: ms="إيجابي 🟢"

    v5=float(df["Volume"].tail(5).mean())
    v20=float(df["Volume"].tail(20).mean())
    vs="حجم مرتفع 🟢" if v5>v20*1.2 else "حجم طبيعي 🟡"

    if bb_l and price<bb_l: bbs="أسفل البولينجر 🟢"; score+=1
    elif bb_u and price>bb_u: bbs="أعلى البولينجر 🔴"; score-=1
    else: bbs="داخل النطاق 🟡"

    # AI Pattern detection (simple)
    closes=df["Close"].tail(20).values
    patterns=[]
    if all(closes[i]<closes[i+1] for i in range(len(closes)-5,len(closes)-1)):
        patterns.append("زخم صاعد قوي")
    if all(closes[i]>closes[i+1] for i in range(len(closes)-5,len(closes)-1)):
        patterns.append("زخم هابط قوي")
    if not patterns: patterns.append("لا توجد أنماط واضحة")

    return dict(trend=trend,ma50=ma50,ma200=ma200,rsi=rsi,rs=rs,
                macd=macd,macd_s=macd_s,ms=ms,vs=vs,bbs=bbs,
                sup=sup,res=res,score=score,patterns=patterns)

# ── Fundamental ───────────────────────────────────────────────────────────────────
def analyze_fund(info):
    fields=dict(rev="totalRevenue",earn="netIncomeToCommon",roe="returnOnEquity",
                roa="returnOnAssets",debt="debtToEquity",fcf="freeCashflow",
                rg="revenueGrowth",eg="earningsGrowth",pe="trailingPE",
                fpe="forwardPE",pb="priceToBook",ps="priceToSalesTrailing12Months",
                gm="grossMargins",om="operatingMargins",npm="profitMargins",
                cr="currentRatio",beta="beta",shares="sharesOutstanding",
                eps="trailingEps",div="dividendYield",payout="payoutRatio")
    d={k:safe(info,v) for k,v in fields.items()}
    score=0
    if d["roe"]  and float(d["roe"]) >=0.15: score+=2
    if d["roa"]  and float(d["roa"]) >=0.08: score+=2
    if d["debt"] and float(d["debt"])<=1.0:  score+=2
    if d["fcf"]  and float(d["fcf"]) >0:     score+=2
    if d["rg"]   and float(d["rg"])  >=0.10: score+=1
    if d["eg"]   and float(d["eg"])  >=0.10: score+=1
    d["score"]=score
    return d

# ── Fair Value ────────────────────────────────────────────────────────────────────
def fair_value(info):
    price=safe(info,"currentPrice") or safe(info,"regularMarketPrice")
    pe=safe(info,"trailingPE"); eps=safe(info,"trailingEps")
    bv=safe(info,"bookValue");  fpe=safe(info,"forwardPE")
    eg=safe(info,"earningsGrowth") or 0.10
    ests=[]
    try:
        if pe and eps and float(eps)>0:
            ests.append(float(eps)*min(float(pe)*0.9,25))
        if eps and bv and float(eps)>0 and float(bv)>0:
            ests.append((22.5*float(eps)*float(bv))**0.5)
        if eps and float(eps)>0:
            g=min(max(float(eg),0.03),0.25); disc=0.10
            dcf=sum([float(eps)*(1+g)**i/(1+disc)**i for i in range(1,6)])
            t=float(eps)*(1+g)**5*15/(1+disc)**5
            ests.append(dcf+t)
        if fpe and eps and float(eps)>0:
            ests.append(float(eps)*min(float(fpe),22))
    except: pass
    if not ests or not price: return None,None,None,1
    f=float(np.median(ests)); iv=float(np.mean(ests))
    disc=(f-float(price))/float(price)
    sc=3 if disc>0.20 else 2 if disc>0 else 1 if disc>-0.15 else 0
    return f,iv,disc,sc

# ── AI Sentiment Analysis (keyword-based) ─────────────────────────────────────────
def analyze_sentiment(text):
    pos=["growth","profit","surge","beat","strong","record","upgrade","buy","bullish","gain","rose","up","positive","exceed"]
    neg=["loss","decline","miss","weak","downgrade","sell","bearish","fall","drop","negative","concern","risk","down","cut"]
    text_lower=text.lower()
    ps=sum(1 for w in pos if w in text_lower)
    ns=sum(1 for w in neg if w in text_lower)
    if ps>ns:   return "إيجابي","pos"
    elif ns>ps: return "سلبي","neg"
    else:       return "محايد","neu"

# ── Decision ─────────────────────────────────────────────────────────────────────
def decide(fs, ts, vs, disc):
    total=fs*0.40+ts*0.35+vs*0.25*3
    cf=min(fs/10,1)*40; ct=min((ts+2)/9,1)*35; cv=(vs/3)*25
    conf=max(20,min(95,round(cf+ct+cv)))
    if total>=7.5:  v="شراء قوي";  css="strong-buy"; col="#3fb950"
    elif total>=5:  v="شراء";      css="buy";        col="#58a6ff"
    elif total>=3:  v="احتفاظ";    css="hold";       col="#d29922"
    elif total>=1:  v="تخفيف";     css="reduce";     col="#f0883e"
    else:           v="بيع";       css="sell";       col="#f85149"
    r=[]
    if fs>=6: r.append("أساسيات قوية")
    if ts>=4: r.append("زخم فني إيجابي")
    if disc and disc>0.10: r.append("مقيّم بأقل من قيمته")
    if not r:
        if fs<4: r.append("أساسيات ضعيفة")
        if ts<0: r.append("اتجاه فني سلبي")
        if disc and disc<-0.20: r.append("مبالغ في تسعيره")
    if not r: r=["تحليل مختلط"]
    return v,css,col,conf," | ".join(r)

# ── Charts ────────────────────────────────────────────────────────────────────────
def chart_price(df, ticker, sup, res):
    fig=make_subplots(rows=3,cols=1,shared_xaxes=True,
                      row_heights=[0.55,0.25,0.20],vertical_spacing=0.03)
    fig.add_trace(go.Candlestick(x=df.index,open=df["Open"],high=df["High"],
        low=df["Low"],close=df["Close"],
        increasing_line_color="#3fb950",decreasing_line_color="#f85149",name="السعر"),row=1,col=1)
    for col,nm,c in [("MA20","MA20","#f0883e"),("MA50","MA50","#58a6ff"),("MA200","MA200","#bc8cff")]:
        fig.add_trace(go.Scatter(x=df.index,y=df[col],line=dict(color=c,width=1.5),name=nm),row=1,col=1)
    fig.add_trace(go.Scatter(x=df.index,y=df["BB_U"],
        line=dict(color="#30363d",width=1,dash="dot"),showlegend=False),row=1,col=1)
    fig.add_trace(go.Scatter(x=df.index,y=df["BB_L"],
        line=dict(color="#30363d",width=1,dash="dot"),
        fill="tonexty",fillcolor="rgba(88,166,255,0.05)",showlegend=False),row=1,col=1)
    fig.add_hline(y=sup,line_dash="dot",line_color="#3fb950",
                  annotation_text=f"دعم {sup:.2f}",row=1,col=1)
    fig.add_hline(y=res,line_dash="dot",line_color="#f85149",
                  annotation_text=f"مقاومة {res:.2f}",row=1,col=1)
    colors=["#3fb950" if c>=o else "#f85149" for c,o in zip(df["Close"],df["Open"])]
    fig.add_trace(go.Bar(x=df.index,y=df["Volume"],marker_color=colors,name="الحجم",opacity=0.7),row=2,col=1)
    fig.add_trace(go.Scatter(x=df.index,y=df["RSI"],line=dict(color="#d29922",width=1.5),name="RSI"),row=3,col=1)
    fig.add_hline(y=70,line_dash="dash",line_color="#f85149",row=3,col=1)
    fig.add_hline(y=30,line_dash="dash",line_color="#3fb950",row=3,col=1)
    fig.update_layout(title=f"📊 {ticker}",height=650,xaxis_rangeslider_visible=False,**CHART_BG)
    return fig

def chart_macd(df):
    fig=go.Figure()
    colors=["#3fb950" if v>=0 else "#f85149" for v in df["MACD_H"]]
    fig.add_trace(go.Bar(x=df.index,y=df["MACD_H"],marker_color=colors,name="Histogram",opacity=0.7))
    fig.add_trace(go.Scatter(x=df.index,y=df["MACD"],line=dict(color="#58a6ff",width=1.5),name="MACD"))
    fig.add_trace(go.Scatter(x=df.index,y=df["MACD_S"],line=dict(color="#f0883e",width=1.5),name="Signal"))
    fig.update_layout(title="MACD",height=260,**CHART_BG)
    return fig

def chart_compare(data):
    fig=go.Figure()
    colors=["#58a6ff","#3fb950","#bc8cff","#f0883e","#d29922"]
    for i,(tk,df) in enumerate(data.items()):
        norm=df["Close"]/df["Close"].iloc[0]*100
        fig.add_trace(go.Scatter(x=df.index,y=norm,
            line=dict(color=colors[i%len(colors)],width=2),name=tk))
    fig.update_layout(title="مقارنة الأداء (مُعاد تأسيسه = 100)",height=380,**CHART_BG)
    return fig

def chart_portfolio(rows):
    labels=[r[0] for r in rows]
    values=[r[5] for r in rows]
    colors=["#58a6ff","#3fb950","#bc8cff","#f0883e","#d29922","#f85149"]
    fig=go.Figure(go.Pie(labels=labels,values=values,
        marker=dict(colors=colors),hole=0.45,textinfo="label+percent"))
    fig.update_layout(title="توزيع المحفظة",height=320,**CHART_BG)
    return fig

# ── AI Forecast (simple momentum-based) ──────────────────────────────────────────
def ai_forecast(hist, price):
    try:
        df=hist.copy()
        c=df["Close"]
        ret_1m = (c.iloc[-1]/c.iloc[-22]-1)*100 if len(c)>22 else 0
        ret_3m = (c.iloc[-1]/c.iloc[-66]-1)*100 if len(c)>66 else 0
        ret_6m = (c.iloc[-1]/c.iloc[-132]-1)*100 if len(c)>132 else 0
        vol_ann= c.pct_change().std()*np.sqrt(252)*100

        score=0
        if ret_1m>0: score+=1
        if ret_3m>0: score+=2
        if ret_6m>0: score+=2
        if vol_ann<30: score+=1

        if score>=5:   outlook="إيجابي 📈";   target=price*1.12
        elif score>=3: outlook="محايد ↔️";    target=price*1.04
        else:          outlook="سلبي 📉";     target=price*0.95

        return dict(
            ret_1m=ret_1m, ret_3m=ret_3m, ret_6m=ret_6m,
            vol=vol_ann, outlook=outlook, target=target, score=score
        )
    except: return None

# ── PDF Report ────────────────────────────────────────────────────────────────────
def generate_report_text(ticker, name, price, cur, verdict, conf, tech, fund, fv, iv, disc, forecast):
    lines=[
        f"{'='*60}",
        f"  تقرير تحليل السهم — محلل الأسهم الذكي Pro v3",
        f"{'='*60}",
        f"السهم:          {ticker} — {name}",
        f"السعر الحالي:   {price:,.2f} {cur}",
        f"التاريخ:        {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"{'─'*60}",
        f"التوصية: {verdict}   |   درجة الثقة: {conf}%",
        f"{'─'*60}",
        "التحليل الفني:",
        f"  الاتجاه:       {tech['trend']}",
        f"  MA50:          {tech['ma50']:,.2f}" if tech['ma50'] else "  MA50:  —",
        f"  MA200:         {tech['ma200']:,.2f}" if tech['ma200'] else "  MA200: —",
        f"  RSI:           {tech['rsi']:.1f} — {tech['rs']}" if tech['rsi'] else "  RSI:   —",
        f"  MACD:          {tech['ms']}",
        f"  الدعم:         {tech['sup']:,.2f}",
        f"  المقاومة:      {tech['res']:,.2f}",
        f"{'─'*60}",
        "التحليل الأساسي:",
        f"  ROE:           {pct(fund['roe'])}",
        f"  ROA:           {pct(fund['roa'])}",
        f"  نمو الإيرادات: {pct(fund['rg'])}",
        f"  نمو الأرباح:   {pct(fund['eg'])}",
        f"  P/E:           {fmt(fund['pe'],'x')}",
        f"{'─'*60}",
        "التقييم العادل:",
        f"  السعر العادل:  {fv:,.2f} {cur}" if fv else "  السعر العادل: —",
        f"  القيمة الجوهرية: {iv:,.2f} {cur}" if iv else "  القيمة الجوهرية: —",
        f"  نسبة الخصم:   {disc*100:+.1f}%" if disc is not None else "  نسبة الخصم: —",
        f"{'─'*60}",
        "توقعات AI:",
        f"  العائد شهر:    {forecast['ret_1m']:+.1f}%" if forecast else "  —",
        f"  العائد 3 أشهر: {forecast['ret_3m']:+.1f}%" if forecast else "  —",
        f"  التوقعات:      {forecast['outlook']}" if forecast else "  —",
        f"  الهدف المتوقع: {forecast['target']:,.2f} {cur}" if forecast else "  —",
        f"{'='*60}",
        "تنبيه: هذا التقرير لأغراض تعليمية فقط وليس توصية استثمارية.",
        f"{'='*60}",
    ]
    return "\n".join(lines)

# ── Check Alerts ──────────────────────────────────────────────────────────────────
def check_alerts(current_price, ticker):
    triggered=[]
    for a in st.session_state.alerts:
        if a["ticker"]==ticker:
            if a["type"]=="أعلى من" and current_price>=a["price"]:
                triggered.append(a)
            elif a["type"]=="أقل من" and current_price<=a["price"]:
                triggered.append(a)
    return triggered

# ══════════════════════════════════════════════════════════════════════════════════
# ── Pages ────────────────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════════

def page_analysis():
    c1,c2,c3=st.columns([3,2,2])
    with c1: sym=st.text_input("🔎 رمز السهم",placeholder="مثال: 2222 | AAPL | 7203 | HSBA")
    with c2: mkt=st.selectbox("🌍 السوق",list(MARKETS.keys()))
    with c3:
        st.markdown("<br>",unsafe_allow_html=True)
        go_btn=st.button("📊 تحليل السهم",use_container_width=True)

    if not (go_btn and sym.strip()):
        st.markdown("""
        <div style="text-align:center;padding:3rem 1rem;color:#8b949e;">
          <div style="font-size:3rem">📊</div>
          <div style="font-size:1.15rem;font-weight:700;color:#e6edf3;margin:.6rem 0 .3rem">جاهز للتحليل</div>
          <div>أدخل رمز السهم واختر السوق</div>
          <div style="margin-top:1rem;font-size:.82rem;display:flex;justify-content:center;gap:1.5rem;flex-wrap:wrap;">
            <span>🇸🇦 2222 | 1120 | 2010</span>
            <span>🇺🇸 AAPL | MSFT | TSLA</span>
            <span>🇬🇧 HSBA | BP | VOD</span>
            <span>🇩🇪 SAP | BMW | VOW3</span>
          </div>
        </div>""",unsafe_allow_html=True)
        return

    mc=MARKETS[mkt]; ticker=get_ticker(sym.strip(),mc)

    with st.spinner(f"⏳ جارٍ جلب بيانات {ticker}…"):
        info,hist,stk=fetch_stock(ticker)

    if info is None or hist is None or hist.empty:
        st.error(f"❌ لم يُعثر على بيانات للرمز **{ticker}**")
        return

    price=safe(info,"currentPrice") or safe(info,"regularMarketPrice")
    if not price:
        try: price=float(hist["Close"].iloc[-1])
        except: pass
    if not price: st.error("❌ تعذّر الحصول على السعر."); return

    price=float(price)
    name=safe(info,"longName") or safe(info,"shortName") or ticker
    cur=safe(info,"currency","—")

    df,sup,res=compute_tech(hist)
    tech=analyze_tech(df,sup,res,price)
    fund=analyze_fund(info)
    fv,iv,disc,vs=fair_value(info)
    verdict,vcss,vcol,conf,reason=decide(fund["score"],tech["score"],vs,disc)
    forecast=ai_forecast(hist,price)

    # Save to history
    st.session_state.history.append({
        "ticker":ticker,"name":name,"price":price,"cur":cur,
        "verdict":verdict,"conf":conf,"time":datetime.now().strftime("%Y-%m-%d %H:%M")
    })

    # Check alerts
    triggered=check_alerts(price,ticker)
    for a in triggered:
        st.warning(f"🔔 تنبيه: {ticker} وصل {price:,.2f} ({a['type']} {a['price']:,.2f})")

    prev=float(hist["Close"].iloc[-2]) if len(hist)>1 else price
    chg=price-prev; chgp=chg/prev*100

    # Header card
    st.markdown(f"""
    <div class="card" style="border-color:{vcol}">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:.8rem">
        <div>
          <div style="font-size:1.3rem;font-weight:900;color:{vcol}">{ticker}</div>
          <div style="color:#8b949e;font-size:.88rem">{name}</div>
          <div style="font-size:.75rem;color:#8b949e;margin-top:.2rem">🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
        </div>
        <div style="text-align:center">
          <div style="font-size:2.6rem;font-weight:900;color:{vcol}">{price:,.2f}</div>
          <div style="color:#8b949e;font-size:.82rem">{cur}</div>
          <div style="color:{'#3fb950' if chg>=0 else '#f85149'};font-size:.9rem;font-weight:700">
            {'▲' if chg>=0 else '▼'} {abs(chg):,.2f} ({abs(chgp):.2f}%)
          </div>
        </div>
        <div style="text-align:center">
          <div style="font-size:.72rem;color:#8b949e">التوصية</div>
          <div style="font-size:1.3rem;font-weight:900;color:{vcol}">{verdict}</div>
          <div style="font-size:.72rem;color:#8b949e">ثقة {conf}%</div>
        </div>
      </div>
    </div>""",unsafe_allow_html=True)

    # Quick metrics
    w52h=safe(info,"fiftyTwoWeekHigh"); w52l=safe(info,"fiftyTwoWeekLow")
    vol=safe(info,"volume") or safe(info,"regularMarketVolume")
    mcap=safe(info,"marketCap"); pe=safe(info,"trailingPE")
    div_y=safe(info,"dividendYield"); beta=safe(info,"beta")

    m1,m2,m3,m4,m5,m6=st.columns(6)
    m1.metric("52أ أعلى",f"{float(w52h):,.2f}" if w52h else "—")
    m2.metric("52أ أدنى",f"{float(w52l):,.2f}" if w52l else "—")
    m3.metric("الحجم",fmt(vol))
    m4.metric("القيمة السوقية",fmt(mcap))
    m5.metric("P/E",f"{float(pe):.1f}x" if pe else "—")
    m6.metric("بيتا",f"{float(beta):.2f}" if beta else "—")

    # Tabs
    tabs=st.tabs(["📈 الرسم البياني","🏢 الأساسي","🔬 الفني",
                  "🤖 AI والتوقعات","📰 الأخبار","🎯 التوصية"])

    with tabs[0]:
        st.plotly_chart(chart_price(df,ticker,sup,res),use_container_width=True)
        st.plotly_chart(chart_macd(df),use_container_width=True)

    with tabs[1]:
        st.markdown('<div class="section-title">🏢 البيانات المالية</div>',unsafe_allow_html=True)
        rows=[
            ("الإيرادات",fmt(fund["rev"]),sbadge(fund["rg"],0.10,-0.05)),
            ("صافي الأرباح",fmt(fund["earn"]),sbadge(fund["earn"],0,None)),
            ("نمو الإيرادات",pct(fund["rg"]),sbadge(fund["rg"],0.10,-0.05)),
            ("نمو الأرباح",pct(fund["eg"]),sbadge(fund["eg"],0.10,-0.05)),
            ("هامش الربح الإجمالي",pct(fund["gm"]),sbadge(fund["gm"],0.40,0.15)),
            ("هامش التشغيل",pct(fund["om"]),sbadge(fund["om"],0.20,0.05)),
            ("هامش صافي الربح",pct(fund["npm"]),sbadge(fund["npm"],0.15,0.03)),
            ("ROE",pct(fund["roe"]),sbadge(fund["roe"],0.15,0.05)),
            ("ROA",pct(fund["roa"]),sbadge(fund["roa"],0.08,0.02)),
            ("نسبة الدين/الملكية",f'{float(fund["debt"]):.2f}x' if fund["debt"] else "—",badge("متوسط","yellow")),
            ("نسبة السيولة",f'{float(fund["cr"]):.2f}x' if fund["cr"] else "—",sbadge(fund["cr"],2.0,1.0)),
            ("التدفق النقدي الحر",fmt(fund["fcf"]),sbadge(fund["fcf"],0,None)),
            ("P/E",f'{float(fund["pe"]):.1f}x' if fund["pe"] else "—",badge("مؤشر التقييم","blue")),
            ("P/B",f'{float(fund["pb"]):.2f}x' if fund["pb"] else "—",badge("مؤشر التقييم","blue")),
            ("EPS",fmt(fund["eps"]),sbadge(fund["eps"],0,None)),
            ("توزيعات الأرباح",pct(fund["div"]),badge("دخل ثابت","purple") if fund["div"] else badge("لا يوجد","yellow")),
            ("نسبة التوزيع",pct(fund["payout"]),sbadge(fund["payout"] and (1-float(fund["payout"])),0.30,0) if fund["payout"] else badge("—","blue")),
            ("بيتا (المخاطرة)",f'{float(fund["beta"]):.2f}' if fund["beta"] else "—",
             badge("مستقر","green") if fund["beta"] and float(fund["beta"])<1 else badge("متقلب","yellow")),
        ]
        tbl='<table class="pro-table"><thead><tr><th>المؤشر</th><th>القيمة</th><th>التقييم</th></tr></thead><tbody>'
        for l,v,b in rows: tbl+=f'<tr><td>{l}</td><td>{v}</td><td>{b}</td></tr>'
        st.markdown(tbl+'</tbody></table>',unsafe_allow_html=True)

    with tabs[2]:
        st.markdown('<div class="section-title">🔬 المؤشرات الفنية</div>',unsafe_allow_html=True)
        tr=[
            ("الاتجاه العام",tech["trend"]),
            ("MA20",f'{tech["ma50"]:,.2f}' if tech["ma50"] else "—"),
            ("MA50",f'{tech["ma50"]:,.2f}' if tech["ma50"] else "—"),
            ("MA200",f'{tech["ma200"]:,.2f}' if tech["ma200"] else "—"),
            ("RSI (14)",f'{tech["rsi"]:.1f} — {tech["rs"]}' if tech["rsi"] else "—"),
            ("MACD",f'{tech["macd"]:.3f} — {tech["ms"]}'),
            ("بولينجر باندز",tech["bbs"]),
            ("الدعم",f'{tech["sup"]:,.2f}'),
            ("المقاومة",f'{tech["res"]:,.2f}'),
            ("حجم التداول",tech["vs"]),
            ("الأنماط المكتشفة"," | ".join(tech["patterns"])),
        ]
        tbl='<table class="pro-table"><thead><tr><th>المؤشر</th><th>القيمة / الإشارة</th></tr></thead><tbody>'
        for l,v in tr: tbl+=f'<tr><td>{l}</td><td>{v}</td></tr>'
        st.markdown(tbl+'</tbody></table>',unsafe_allow_html=True)

    with tabs[3]:
        st.markdown('<div class="section-title">🤖 تحليل AI والتوقعات</div>',unsafe_allow_html=True)
        if forecast:
            st.markdown(f"""
            <div class="ai-box">
              <div class="ai-title">🤖 تحليل الزخم والتوقعات</div>
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:.8rem;font-size:.88rem">
                <div>📅 العائد شهر: <b style="color:{'#3fb950' if forecast['ret_1m']>=0 else '#f85149'}">{forecast['ret_1m']:+.1f}%</b></div>
                <div>📅 العائد 3 أشهر: <b style="color:{'#3fb950' if forecast['ret_3m']>=0 else '#f85149'}">{forecast['ret_3m']:+.1f}%</b></div>
                <div>📅 العائد 6 أشهر: <b style="color:{'#3fb950' if forecast['ret_6m']>=0 else '#f85149'}">{forecast['ret_6m']:+.1f}%</b></div>
                <div>📊 التقلب السنوي: <b>{forecast['vol']:.1f}%</b></div>
                <div>🎯 التوقعات: <b>{forecast['outlook']}</b></div>
                <div>🎯 السعر المستهدف: <b style="color:#58a6ff">{forecast['target']:,.2f} {cur}</b></div>
              </div>
            </div>""",unsafe_allow_html=True)

            # Forecast chart
            future_dates=[hist.index[-1]+timedelta(days=i*7) for i in range(1,9)]
            g=0.02 if forecast["score"]>=5 else 0.005 if forecast["score"]>=3 else -0.01
            future_prices=[price*(1+g)**i for i in range(1,9)]
            fig=go.Figure()
            fig.add_trace(go.Scatter(x=hist.index[-60:],y=hist["Close"].tail(60),
                line=dict(color="#58a6ff",width=2),name="السعر الفعلي"))
            fig.add_trace(go.Scatter(x=future_dates,y=future_prices,
                line=dict(color="#3fb950",width=2,dash="dash"),name="التوقع"))
            fig.update_layout(title="توقع مسار السعر (8 أسابيع)",height=300,**CHART_BG)
            st.plotly_chart(fig,use_container_width=True)
        else:
            st.info("لا تتوفر بيانات كافية للتوقع")

        # Fair Value breakdown
        st.markdown('<div class="section-title">💰 تفصيل التقييم العادل</div>',unsafe_allow_html=True)
        fv_rows=[
            ("السعر الحالي",f"{price:,.2f} {cur}"),
            ("السعر العادل (متوسط الطرق)",f"{fv:,.2f} {cur}" if fv else "—"),
            ("القيمة الجوهرية (معدل)",f"{iv:,.2f} {cur}" if iv else "—"),
            ("نسبة الخصم / المبالغة",f"{disc*100:+.1f}%" if disc is not None else "—"),
            ("التقييم",badge("مقيّم بأقل","green") if disc and disc>0.10
             else badge("عادل","yellow") if disc and disc>-0.10
             else badge("مبالغ فيه","red")),
        ]
        tbl='<table class="pro-table"><thead><tr><th>البند</th><th>القيمة</th></tr></thead><tbody>'
        for k,v in fv_rows: tbl+=f'<tr><td>{k}</td><td>{v}</td></tr>'
        st.markdown(tbl+'</tbody></table>',unsafe_allow_html=True)

    with tabs[4]:
        st.markdown('<div class="section-title">📰 آخر الأخبار والمشاعر</div>',unsafe_allow_html=True)
        with st.spinner("جارٍ جلب الأخبار…"):
            news=fetch_news(ticker)
        if news:
            pos_count=neg_count=neu_count=0
            for item in news:
                title=item.get("title","")
                pub=item.get("providerPublishTime",0)
                link=item.get("link","#")
                pub_str=datetime.fromtimestamp(pub).strftime("%Y-%m-%d %H:%M") if pub else "—"
                sent,skind=analyze_sentiment(title)
                if skind=="pos": pos_count+=1
                elif skind=="neg": neg_count+=1
                else: neu_count+=1
                sent_css=f"news-sent-{skind}"
                st.markdown(f"""
                <div class="news-item">
                  <div class="news-title">{title}</div>
                  <div class="news-meta">
                    🕐 {pub_str} &nbsp;|&nbsp;
                    المشاعر: <span class="{sent_css}">{sent}</span> &nbsp;|&nbsp;
                    <a href="{link}" target="_blank" style="color:#58a6ff">اقرأ المزيد ↗</a>
                  </div>
                </div>""",unsafe_allow_html=True)

            # Sentiment summary
            total=pos_count+neg_count+neu_count
            if total:
                st.markdown(f"""
                <div class="card" style="margin-top:.8rem">
                  <div class="section-title">ملخص مشاعر الأخبار</div>
                  <div style="display:flex;gap:1.5rem;flex-wrap:wrap;font-size:.9rem">
                    <span>🟢 إيجابي: <b>{pos_count}</b> ({pos_count/total*100:.0f}%)</span>
                    <span>🔴 سلبي: <b>{neg_count}</b> ({neg_count/total*100:.0f}%)</span>
                    <span>🟡 محايد: <b>{neu_count}</b> ({neu_count/total*100:.0f}%)</span>
                  </div>
                </div>""",unsafe_allow_html=True)
        else:
            st.info("لا تتوفر أخبار حالياً لهذا السهم")

    with tabs[5]:
        st.markdown('<div class="section-title">🎯 القرار النهائي</div>',unsafe_allow_html=True)
        st.markdown(f"""
        <div class="verdict-box v-{vcss}">
          <div class="verdict-title" style="color:{vcol}">{verdict}</div>
          <div class="verdict-sub">{reason}</div>
        </div>""",unsafe_allow_html=True)

        cf_v=min(fund["score"]/10,1)*40
        ct_v=min((tech["score"]+2)/9,1)*35
        cv_v=(vs/3)*25
        st.markdown(f"""
        <div class="conf-wrap">
          <div class="conf-row"><span>التحليل الأساسي (40%)</span><span>{cf_v:.0f}/40</span></div>
          <div class="conf-track"><div class="conf-fill" style="width:{cf_v/40*100}%;background:#3fb950"></div></div>
        </div>
        <div class="conf-wrap">
          <div class="conf-row"><span>التحليل الفني (35%)</span><span>{ct_v:.0f}/35</span></div>
          <div class="conf-track"><div class="conf-fill" style="width:{ct_v/35*100}%;background:#58a6ff"></div></div>
        </div>
        <div class="conf-wrap">
          <div class="conf-row"><span>التقييم العادل (25%)</span><span>{cv_v:.0f}/25</span></div>
          <div class="conf-track"><div class="conf-fill" style="width:{cv_v/25*100}%;background:#bc8cff"></div></div>
        </div>
        <div class="conf-wrap" style="margin-top:.6rem">
          <div class="conf-row" style="font-weight:700"><span>درجة الثقة الإجمالية</span><span>{conf}/100</span></div>
          <div class="conf-track" style="height:11px"><div class="conf-fill"
            style="width:{conf}%;background:linear-gradient(90deg,#58a6ff,#bc8cff)"></div></div>
        </div>""",unsafe_allow_html=True)

        st.markdown('<div class="section-title">📋 ملخص المخرجات الاستثمارية</div>',unsafe_allow_html=True)
        sl=price*0.93
        t1_=res if res>price else price*1.08
        t2_=t1_*1.10; t12=(fv or price)*1.05
        bl=sup if sup<price else price*0.97; bh=price*1.02
        sum_rows=[
            ("السعر الحالي",f"{price:,.2f} {cur}"),
            ("السعر العادل",f"{fv:,.2f} {cur}" if fv else "—"),
            ("القيمة الجوهرية",f"{iv:,.2f} {cur}" if iv else "—"),
            ("نسبة الخصم/المبالغة",f"{disc*100:+.1f}%" if disc is not None else "—"),
            ("أفضل منطقة شراء",f"{bl:,.2f} – {bh:,.2f} {cur}"),
            ("وقف الخسارة",f"{sl:,.2f} {cur}"),
            ("الهدف الأول",f"{t1_:,.2f} {cur}"),
            ("الهدف الثاني",f"{t2_:,.2f} {cur}"),
            ("هدف 12 شهر",f"{t12:,.2f} {cur}"),
            ("هدف AI",f"{forecast['target']:,.2f} {cur}" if forecast else "—"),
            ("درجة الثقة",f"{conf}/100"),
            ("التوصية النهائية",verdict),
        ]
        tbl='<table class="pro-table"><thead><tr><th>البند</th><th>القيمة</th></tr></thead><tbody>'
        for k,v in sum_rows:
            cs=f"color:{vcol};font-weight:700" if k=="التوصية النهائية" else ""
            tbl+=f'<tr><td>{k}</td><td style="{cs}">{v}</td></tr>'
        st.markdown(tbl+'</tbody></table>',unsafe_allow_html=True)

        # Download Report
        st.markdown('<div class="section-title">📄 تصدير التقرير</div>',unsafe_allow_html=True)
        report=generate_report_text(ticker,name,price,cur,verdict,conf,tech,fund,fv,iv,disc,forecast)
        st.download_button(
            label="⬇️ تحميل التقرير النصي",
            data=report.encode("utf-8"),
            file_name=f"report_{ticker}_{datetime.now().strftime('%Y%m%d')}.txt",
            mime="text/plain"
        )

    st.markdown("""
    <div class="disclaimer">
      ⚠️ <b>إخلاء المسؤولية:</b> هذا التحليل لأغراض تعليمية فقط وليس توصية استثمارية.
      البيانات من Yahoo Finance. الاستثمار ينطوي على مخاطر.
    </div>""",unsafe_allow_html=True)


def page_compare():
    st.markdown('<div class="section-title">⚖️ مقارنة الأسهم</div>',unsafe_allow_html=True)
    cols=st.columns(5)
    syms=[]
    for i,c in enumerate(cols):
        with c:
            t=st.text_input(f"سهم {i+1}",key=f"cmp{i}",placeholder="رمز")
            if t.strip(): syms.append(t.strip().upper())
    mkt=st.selectbox("السوق",list(MARKETS.keys()),key="cmp_mkt")
    if st.button("📊 قارن الآن",key="cmpbtn") and syms:
        mc=MARKETS[mkt]; data={}; crows=[]
        with st.spinner("جارٍ جلب البيانات…"):
            for s in syms:
                tk=get_ticker(s,mc)
                info,hist,_=fetch_stock(tk)
                if hist is not None and not hist.empty:
                    data[tk]=hist
                    p=safe(info,"currentPrice") or safe(info,"regularMarketPrice")
                    pe=safe(info,"trailingPE"); roe=safe(info,"returnOnEquity")
                    mcap=safe(info,"marketCap"); w52h=safe(info,"fiftyTwoWeekHigh")
                    w52l=safe(info,"fiftyTwoWeekLow"); div=safe(info,"dividendYield")
                    ytd=(float(p)/float(w52l)-1)*100 if p and w52l else None
                    crows.append((tk,fmt(p),f"{float(pe):.1f}x" if pe else "—",
                                  pct(roe),fmt(mcap),
                                  f"{ytd:.1f}%" if ytd else "—",
                                  pct(div) if div else "—"))
        if data: st.plotly_chart(chart_compare(data),use_container_width=True)
        if crows:
            tbl='<table class="pro-table"><thead><tr>'
            for h in ["السهم","السعر","P/E","ROE","القيمة السوقية","من أدنى 52أ","التوزيعات"]:
                tbl+=f'<th>{h}</th>'
            tbl+='</tr></thead><tbody>'
            for r in crows: tbl+='<tr>'+''.join(f'<td>{v}</td>' for v in r)+'</tr>'
            st.markdown(tbl+'</tbody></table>',unsafe_allow_html=True)


def page_portfolio():
    st.markdown('<div class="section-title">💼 المحفظة الاستثمارية</div>',unsafe_allow_html=True)
    with st.expander("➕ إضافة سهم",expanded=False):
        c1,c2,c3,c4=st.columns(4)
        with c1: pt=st.text_input("رمز السهم",key="pft")
        with c2: pm=st.selectbox("السوق",list(MARKETS.keys()),key="pfm")
        with c3: ps=st.number_input("عدد الأسهم",min_value=1,value=10,key="pfs")
        with c4: pp=st.number_input("سعر الشراء",min_value=0.01,value=100.0,key="pfp")
        if st.button("➕ إضافة",key="pfadd") and pt:
            mc=MARKETS[pm]; tk=get_ticker(pt,mc)
            st.session_state.portfolio.append({
                "ticker":tk,"shares":ps,"buy_price":pp,
                "market":pm,"date":datetime.now().strftime("%Y-%m-%d")
            })
            st.success(f"✅ تمت إضافة {tk}")

    if not st.session_state.portfolio:
        st.info("المحفظة فارغة — أضف أسهمك أعلاه"); return

    rows=[]; tc=tv=0
    for item in st.session_state.portfolio:
        info,hist,_=fetch_stock(item["ticker"])
        if info and hist is not None and not hist.empty:
            p=safe(info,"currentPrice") or safe(info,"regularMarketPrice")
            if not p:
                try: p=float(hist["Close"].iloc[-1])
                except: continue
            p=float(p)
            cost=item["shares"]*item["buy_price"]
            val=item["shares"]*p; pnl=val-cost; pp=pnl/cost*100
            tc+=cost; tv+=val
            rows.append((item["ticker"],item["shares"],item["buy_price"],p,cost,val,pnl,pp))

    if rows:
        tpnl=tv-tc
        m1,m2,m3,m4=st.columns(4)
        m1.metric("💰 إجمالي التكلفة",fmt(tc))
        m2.metric("📈 القيمة الحالية",fmt(tv))
        m3.metric("💹 الربح/الخسارة",fmt(tpnl),
                  delta=f"{(tv/tc-1)*100:.1f}%" if tc else None)
        m4.metric("📊 العائد الإجمالي",f"{(tv/tc-1)*100:.1f}%" if tc else "—")

        st.plotly_chart(chart_portfolio(rows),use_container_width=True)

        tbl='<table class="pro-table"><thead><tr>'
        for h in ["السهم","الأسهم","الشراء","الحالي","التكلفة","القيمة","الربح","النسبة"]:
            tbl+=f'<th>{h}</th>'
        tbl+='</tr></thead><tbody>'
        for r in rows:
            col="#3fb950" if r[6]>=0 else "#f85149"
            sg="+" if r[6]>=0 else ""
            tbl+=f'<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]:,.2f}</td>'
            tbl+=f'<td>{r[3]:,.2f}</td><td>{fmt(r[4])}</td><td>{fmt(r[5])}</td>'
            tbl+=f'<td style="color:{col}">{sg}{fmt(r[6])}</td>'
            tbl+=f'<td style="color:{col}">{sg}{r[7]:.1f}%</td></tr>'
        st.markdown(tbl+'</tbody></table>',unsafe_allow_html=True)

        if st.button("🗑️ مسح المحفظة",key="pfclear"):
            st.session_state.portfolio=[]; st.rerun()


def page_alerts():
    st.markdown('<div class="section-title">🔔 تنبيهات السعر</div>',unsafe_allow_html=True)
    with st.expander("➕ إضافة تنبيه",expanded=True):
        c1,c2,c3,c4=st.columns(4)
        with c1: at=st.text_input("رمز السهم",key="alt")
        with c2: am=st.selectbox("السوق",list(MARKETS.keys()),key="alm")
        with c3: atype=st.selectbox("النوع",["أعلى من","أقل من"],key="altype")
        with c4: ap=st.number_input("السعر المستهدف",min_value=0.01,value=100.0,key="alp")
        if st.button("➕ إضافة تنبيه",key="aladd") and at:
            mc=MARKETS[am]; tk=get_ticker(at,mc)
            st.session_state.alerts.append({
                "ticker":tk,"type":atype,"price":ap,
                "date":datetime.now().strftime("%Y-%m-%d %H:%M")
            })
            st.success(f"✅ تنبيه مُضاف: {tk} {atype} {ap:,.2f}")

    if st.session_state.alerts:
        st.markdown('<div class="section-title">قائمة التنبيهات</div>',unsafe_allow_html=True)
        for i,a in enumerate(st.session_state.alerts):
            c1,c2=st.columns([5,1])
            with c1:
                st.markdown(f"""
                <div class="alert-item">
                  <b>{a['ticker']}</b> — {a['type']} <b>{a['price']:,.2f}</b>
                  <span style="color:#8b949e;font-size:.78rem;margin-right:1rem">🕐 {a['date']}</span>
                </div>""",unsafe_allow_html=True)
            with c2:
                if st.button("🗑️",key=f"del_al_{i}"):
                    st.session_state.alerts.pop(i); st.rerun()
    else:
        st.info("لا توجد تنبيهات — أضف تنبيهاً أعلاه")


def page_history():
    st.markdown('<div class="section-title">📜 سجل التحليلات</div>',unsafe_allow_html=True)
    if not st.session_state.history:
        st.info("لم تقم بأي تحليل بعد"); return
    tbl='<table class="pro-table"><thead><tr>'
    for h in ["الوقت","السهم","الاسم","السعر","التوصية","الثقة"]:
        tbl+=f'<th>{h}</th>'
    tbl+='</tr></thead><tbody>'
    for h in reversed(st.session_state.history[-50:]):
        tbl+=f'<tr><td>{h["time"]}</td><td>{h["ticker"]}</td>'
        tbl+=f'<td>{h["name"][:30]}</td><td>{h["price"]:,.2f} {h["cur"]}</td>'
        tbl+=f'<td>{h["verdict"]}</td><td>{h["conf"]}%</td></tr>'
    st.markdown(tbl+'</tbody></table>',unsafe_allow_html=True)
    if st.button("🗑️ مسح السجل"):
        st.session_state.history=[]; st.rerun()


def page_watchlist():
    st.markdown('<div class="section-title">👁️ قائمة المراقبة</div>',unsafe_allow_html=True)
    with st.expander("➕ إضافة سهم للمراقبة",expanded=False):
        c1,c2=st.columns(2)
        with c1: wt=st.text_input("رمز السهم",key="wlt")
        with c2: wm=st.selectbox("السوق",list(MARKETS.keys()),key="wlm")
        if st.button("➕ إضافة",key="wladd") and wt:
            mc=MARKETS[wm]; tk=get_ticker(wt,mc)
            if tk not in [w["ticker"] for w in st.session_state.watchlist]:
                st.session_state.watchlist.append({"ticker":tk,"market":wm})
                st.success(f"✅ تمت إضافة {tk}")

    if not st.session_state.watchlist:
        st.info("قائمة المراقبة فارغة"); return

    st.markdown('<div class="section-title">الأسهم المراقبة — بيانات مباشرة</div>',unsafe_allow_html=True)
    tbl='<table class="pro-table"><thead><tr>'
    for h in ["السهم","السعر","التغيير","52أ أعلى","52أ أدنى","القيمة السوقية","P/E"]:
        tbl+=f'<th>{h}</th>'
    tbl+='</tr></thead><tbody>'

    for item in st.session_state.watchlist:
        info,hist,_=fetch_stock(item["ticker"])
        if info and hist is not None and not hist.empty:
            p=safe(info,"currentPrice") or safe(info,"regularMarketPrice")
            prev=float(hist["Close"].iloc[-2]) if len(hist)>1 else float(p or 0)
            if p:
                chg=(float(p)-prev)/prev*100
                col="#3fb950" if chg>=0 else "#f85149"
                sg="+" if chg>=0 else ""
                tbl+=f'<tr><td>{item["ticker"]}</td>'
                tbl+=f'<td>{float(p):,.2f}</td>'
                tbl+=f'<td style="color:{col}">{sg}{chg:.2f}%</td>'
                tbl+=f'<td>{fmt(safe(info,"fiftyTwoWeekHigh"))}</td>'
                tbl+=f'<td>{fmt(safe(info,"fiftyTwoWeekLow"))}</td>'
                tbl+=f'<td>{fmt(safe(info,"marketCap"))}</td>'
                tbl+=f'<td>{fmt(safe(info,"trailingPE"),"x")}</td></tr>'

    st.markdown(tbl+'</tbody></table>',unsafe_allow_html=True)

    if st.button("🗑️ مسح القائمة",key="wlclear"):
        st.session_state.watchlist=[]; st.rerun()


# ══════════════════════════════════════════════════════════════════════════════════
# ── App ───────────────────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div class="pro-header">
  <h1>📈 محلل الأسهم الذكي Pro v3</h1>
  <p>تحليل شامل • 10 أسواق عالمية • AI • محفظة • تنبيهات • أخبار • بيانات لحظية</p>
</div>""",unsafe_allow_html=True)

page=st.radio("",
    ["🔍 تحليل","⚖️ مقارنة","💼 المحفظة","🔔 التنبيهات","👁️ المراقبة","📜 السجل"],
    horizontal=True, label_visibility="collapsed")

st.markdown("---")

if   page=="🔍 تحليل":    page_analysis()
elif page=="⚖️ مقارنة":   page_compare()
elif page=="💼 المحفظة":  page_portfolio()
elif page=="🔔 التنبيهات": page_alerts()
elif page=="👁️ المراقبة":  page_watchlist()
elif page=="📜 السجل":    page_history()
