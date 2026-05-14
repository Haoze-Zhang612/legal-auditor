import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import plotly.graph_objects as go
from openai import OpenAI
import re
import datetime
import base64
import time

# ================= 1. 页面与学术状态配置 =================
st.set_page_config(page_title="TDM & GDPR Compliance Auditor", page_icon="⚖️", layout="wide")

# ================= 2. 欧盟合规监控引擎 (SPARQL) =================
@st.cache_data(ttl=86400)  # 每天自动刷新一次
def fetch_eu_updates():
    endpoint = "https://publications.europa.eu/webapi/rdf/sparql"
    query = """
    PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
    PREFIX dc: <http://purl.org/dc/elements/1.1/>
    SELECT DISTINCT ?celex ?date ?title
    WHERE {
      ?work a cdm:resource_legal .
      ?work cdm:resource_legal_date_publication ?date .
      ?work dc:title ?title .
      ?work cdm:resource_legal_id_celex ?celex .
      FILTER(lang(?title) = "en")
      FILTER(?date >= "2026-01-01"^^xsd:date)
    }
    ORDER BY DESC(?date) LIMIT 5
    """
    headers = {
        'Accept': 'application/sparql-results+json',
        'User-Agent': 'Haoze-Legal-Tech-Audit-Bot/1.0 (Contact: your_email@fau.de; Purpose: Academic Research)'
    }
    try:
        r = requests.get(endpoint, params={'query': query}, headers=headers, timeout=10)
        return r.json()['results']['bindings'] if r.status_code == 200 else []
    except:
        return []

# 将原有的隐藏 CSS 和 新的背景图 CSS 合并成一个函数
def set_page_bg_and_hide_elements(image_file):
    try:
        with open(image_file, "rb") as f:
            encoded_string = base64.b64encode(f.read()).decode()
        
        css = f"""
        <style>
        #MainMenu {{visibility: hidden;}}
        header {{visibility: hidden;}}
        .stDeployButton {{display: none;}}
        footer {{visibility: hidden;}}
        
        .stApp {{
            background-color: transparent !important;
        }}
        
        .stApp::before {{
            content: "";
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background-image: url(data:image/jpeg;base64,{encoded_string});
            background-size: cover;
            background-position: center;
            opacity: 0.25; 
            z-index: -1;
            pointer-events: none;
        }}
        
        .block-container {{
            background-color: var(--background-color); 
            border-radius: 15px; 
            padding: 3rem 4rem; 
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08); 
            z-index: 1;
            max-width: 1000px; 
        }}

        .stMarkdown p, div[data-testid="stCaptionContainer"] p, .stAlert p {{
            font-family: "Microsoft YaHei", "SimHei", sans-serif !important;
            font-weight: bold !important;
        }}
        </style>
        """
        st.markdown(css, unsafe_allow_html=True)
    except FileNotFoundError:
        st.error(f"🚨 严重错误：找不到背景图片")

set_page_bg_and_hide_elements("bg.jpg")

# ================= 3. 侧边栏 UI 与 实时监控展示 =================
with st.sidebar:
    st.markdown("## 🇪🇺 EU Regulatory Feed")
    st.caption("Real-time monitoring of EU Official Journal")
    
    # 执行抓取逻辑
    updates = fetch_eu_updates()
    if updates:
        for update in updates:
            # 使用 error 样式作为高亮预警
            st.error(f"**Update: {update['date']['value']}**")
            st.markdown(f"**{update['title']['value']}**")
            celex = update['celex']['value']
            url = f"https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:{celex}"
            st.link_button(f"View CELEX: {celex}", url)
            st.divider()
    else:
        st.write("No new updates found.")
        
    st.info("Verified by: **Haoze Legal-Tech Agent**\n\nCompliant with EU Open Data Policy.")

# ================= 4. 系统状态初始化 =================
if 'scan_result' not in st.session_state:
    st.session_state['scan_result'] = None
if 'history' not in st.session_state:
    st.session_state['history'] = []
if 'ai_memo' not in st.session_state:
    st.session_state['ai_memo'] = None

# ================= 5. 国际化与专注法域词库 =================
ui_texts = {
    "English": {
        "title": "⚖️ Legal Tech Auditor",
        "framework_notice": "Jurisdiction: Germany (EU Acquis Applicable)",
        "input_label": "Enter Target URL",
        "btn_scan": "Run Compliance Audit",
        "history_label": "📜 Recent Audits",
        "ai_header": "🤖 Doctrinal AI Analysis",
        "ai_btn": "Generate Doctrinal Memo",
        "key_placeholder": "Paste API Key...",
        "disclaimer": "⚠️ Academic Prototype for EU/DE Law Research. Not Legal Advice.",
        "score_title": "🎯 Overall Compliance Score",
        "report_title": "📑 Empirical Audit Results",
        "tdm_layer": "1. Text & Data Mining (TDM) Reservation",
        "adm_layer": "2. Automated Decision-Making (ADM)",
        "gdpr_layer": "3. Transparency & Privacy (GDPR)",
        "tdm_success": "✅ AI Crawlers Blocked: ",
        "tdm_grey": "⚠️ Grey Area: General bot blocking found, but lacks specific AI directives.",
        "tdm_fail": "❌ No Machine-Readable Reservation Found.",
        "adm_success": "✅ Profiling/ADM keywords detected in policy.",
        "adm_fail": "⚠️ No clear Automated Decision-Making (ADM) declarations found.",
        "policy_success": "✅ Policy Documented: ",
        "policy_fail": "🚨 Critical Transparency Failure (No Privacy Policy Found).",
        "ai_analysis_title": " Analysis Results",
        "ai_tag_status": "Current Doctrinal Status",
        "ai_tag_risk": "Compliance Friction",
        "ai_tag_suggest": "Strategic Mitigation"
    },
    "中文": {
        "title": "⚖️ 自动化审计系统",
        "framework_notice": "适用法域：德国（适用欧盟既有规则）",
        "input_label": "输入目标网址",
        "btn_scan": "开始法理审计",
        "history_label": "📜 最近扫描记录",
        "ai_header": "🤖 AI 法理分析",
        "ai_btn": "生成法理备忘录",
        "key_placeholder": "粘贴 API Key...",
        "disclaimer": "⚠️ 针对欧盟/德国法的学术研究原型。不构成正式法律建议。",
        "score_title": "🎯 综合合规得分",
        "report_title": "📑 深度审计报告",
        "tdm_layer": "1. TDM 权利保留 (§ 44b UrhG)",
        "adm_layer": "2. 自动化决策 (ADM)",
        "gdpr_layer": "3. 透明度与隐私 (GDPR)",
        "tdm_success": "✅ 已明确拦截 AI 爬虫: ",
        "tdm_grey": "⚠️ 灰色地带：发现通用爬虫拦截，但缺乏针对 AI 的明确指令。",
        "tdm_fail": "❌ 未发现机器可读的 TDM 权利保留声明。",
        "adm_success": "✅ 在政策中检测到用户画像/自动化决策 (ADM) 声明。",
        "adm_fail": "⚠️ 未发现明确的自动化决策 (ADM) 透明度声明。",
        "policy_success": "✅ 已定位隐私政策链接: ",
        "policy_fail": "🚨 严重风险: 未发现隐私政策链接。",
        "ai_analysis_title": " 分析结果",
        "ai_tag_status": "合规现状",
        "ai_tag_risk": "核心法理摩擦",
        "ai_tag_suggest": "合规改进建议"
    },
    "Deutsch": {
        "title": "⚖️ Legal-Tech-Auditor",
        "framework_notice": "Rechtsrahmen: Deutschland (unter Anwendung des EU-Acquis)",
        "input_label": "Ziel-URL eingeben",
        "btn_scan": "Rechtsprüfung starten",
        "history_label": "📜 Letzte Prüfungen",
        "ai_header": "🤖 Doktrinäre KI-Analyse",
        "ai_btn": "Doktrinäres Memo generieren",
        "key_placeholder": "API-Key einfügen...",
        "disclaimer": "⚠️ Akademischer Prototyp für die EU/DE-Rechtsforschung. Keine Rechtsberatung.",
        "score_title": "🎯 Gesamt-Compliance-Score",
        "report_title": "📑 Empirische Prüfergebnisse",
        "tdm_layer": "1. TDM-Nutzungsvorbehalt (§ 44b UrhG)",
        "adm_layer": "2. Automatisierte Entscheidungsfindung (ADM)",
        "gdpr_layer": "3. Transparenz & Datenschutz (DSGVO)",
        "tdm_success": "✅ KI-Crawler blockiert: ",
        "tdm_grey": "⚠️ Grauzone: Allgemeine Bot-Blockierung gefunden, aber keine spezifischen KI-Anweisungen.",
        "tdm_fail": "❌ Kein maschinenlesbarer Nutzungsvorbehalt gefunden.",
        "adm_success": "✅ Profiling/ADM-Begriffe in der Richtlinie erkannt.",
        "adm_fail": "⚠️ Keine klaren Erklärungen zur Automatisierten Entscheidungsfindung (ADM) gefunden.",
        "policy_success": "✅ Datenschutzerklärung gefunden: ",
        "policy_fail": "🚨 KRITISCH: Keine Datenschutzerklärung gefunden.",
        "ai_analysis_title": " Analyseergebnis",
        "ai_tag_status": "Doktrinärer Status",
        "ai_tag_risk": "Compliance-Friktion",
        "ai_tag_suggest": "Strategische Minderung"
    }
}

# ================= 6. 高级审计逻辑 =================
def get_ai_config(key):
    if key.startswith("gsk_"): return "Groq", "https://api.groq.com/openai/v1", "llama-3.3-70b-versatile"
    if key.startswith("AIza"): return "Gemini", "https://generativelanguage.googleapis.com/v1beta/openai/", "gemini-1.5-flash"
    if "deepseek" in key.lower() or (key.startswith("sk-") and len(key) < 45): return "DeepSeek", "https://api.deepseek.com", "deepseek-chat"
    return "OpenAI", "https://api.openai.com/v1", "gpt-4o-mini"

def run_academic_audit(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        domain = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        
        ai_bots_blocked = []
        general_bots_blocked = False
        try:
            r_txt = requests.get(f"{domain}/robots.txt", timeout=5).text.lower()
            ai_bots_blocked = [b for b in ['gptbot', 'ccbot', 'anthropic-ai', 'claudebot'] if b in r_txt and 'disallow' in r_txt]
            general_bots_blocked = '*' in r_txt and 'disallow: /' in r_txt
        except: pass
        
        meta = soup.find('meta', attrs={'name': re.compile(r'tdm-reservation', re.I)})
        
        legal_url, legal_text = None, ""
        adm_flag = False
        weights = {'privacy':15, 'datenschutz':15, 'impressum':10}
        
        for a in soup.find_all('a', href=True):
            score = sum(v for k, v in weights.items() if k in a.get_text().lower() or k in a['href'].lower())
            if score > 10:
                legal_url = urljoin(url, a['href'])
                break 
                
        if legal_url:
            l_res = requests.get(legal_url, headers=headers, timeout=5)
            legal_text = BeautifulSoup(l_res.text, 'html.parser').get_text()[:4000]
            adm_flag = any(kw in legal_text.lower() for kw in ['automated decision', 'profiling', 'automatisierte entscheidung'])

        score = 20
        if ai_bots_blocked or meta: score += 30
        if adm_flag: score += 15
        if legal_url: score += 35

        return {
            "url": url, 
            "tdm": {"ai_bots": ai_bots_blocked, "general_bots": general_bots_blocked},
            "privacy": {"policy_url": legal_url, "adm_declared": adm_flag},
            "score": score, "text": legal_text if legal_text else soup.get_text()[:3000]
        }
    except Exception as e:
        st.error(f"Audit Failed: {e}")
        return None

# ================= 7. 交互 UI 布局 =================
_, lang_col = st.columns([5, 1])
with lang_col:
    lang = st.selectbox("Language", ["English", "中文", "Deutsch"], index=0)
t = ui_texts[lang]

st.markdown("<br>", unsafe_allow_html=True)
_, mid, _ = st.columns([1, 4, 1])
with mid:
    st.markdown(f"<h1 style='text-align:center;'>{t['title']}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align:center; color:#888888;'>{t['framework_notice']}</p>", unsafe_allow_html=True)
    
    url_input = st.text_input(t["input_label"], placeholder="https://...", label_visibility="collapsed")
    if st.button(t["btn_scan"], type="primary", use_container_width=True):
        if url_input:
            result = run_academic_audit(url_input)
            if result:
                st.session_state['scan_result'] = result
                st.rerun()

# ================= 8. 审计结果展示 =================
if st.session_state['scan_result']:
    r = st.session_state['scan_result']
    st.markdown("---")
    res_l, res_r = st.columns([1, 1.5])

    with res_l:
        st.subheader(t["score_title"])
        fig = go.Figure(go.Indicator(mode="gauge+number", value=r["score"]))
        fig.update_layout(height=200, paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)

        st.subheader(t["report_title"])
        with st.container(border=True):
            st.markdown(f"**{t['tdm_layer']}**")
            if r["tdm"]["ai_bots"]: st.success(f"{t['tdm_success']}{', '.join(r['tdm']['ai_bots'])}")
            else: st.error(t["tdm_fail"])

    with res_r:
        st.markdown(f"#### {t['ai_header']}")
        api_key = st.text_input("API Key", type="password", placeholder=t["key_placeholder"])
        if st.button(t["ai_btn"], use_container_width=True):
            if api_key:
                with st.spinner("Analyzing..."):
                    vendor, b_url, m_name = get_ai_config(api_key)
                    client = OpenAI(api_key=api_key, base_url=b_url)
                    prompt = f"Audit {r['url']} under EU law. TDM: {r['tdm']['ai_bots']}. Text: {r['text'][:1000]}"
                    response = client.chat.completions.create(model=m_name, messages=[{"role": "user", "content": prompt}])
                    st.session_state['ai_memo'] = (vendor, response.choices[0].message.content)
        
        if st.session_state['ai_memo']:
            st.info(st.session_state['ai_memo'][1])

st.markdown("<br><hr><center><small style='opacity:0.6;'>" + t["disclaimer"] + "</small></center>", unsafe_allow_html=True)