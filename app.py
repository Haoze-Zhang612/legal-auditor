import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import plotly.graph_objects as go
from openai import OpenAI
import re
import datetime
import base64

# ================= 1. 页面与学术状态配置 =================
st.set_page_config(page_title="TDM & GDPR Compliance Auditor", page_icon="⚖️", layout="wide")

# 【自动化爬虫：每小时更新一次，支持关键词检索】
@st.cache_data(ttl=3600)
def fetch_eu_legal_links(keywords=None):
    endpoint = "https://publications.europa.eu/webapi/rdf/sparql"
    # 动态构建关键词过滤：如果没审计，默认查数据保护；审计了就查相关关键词
    kf = f"FILTER(regex(str(?title), '{keywords}', 'i'))" if keywords else ""
    query = f"""
    PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
    PREFIX dc: <http://purl.org/dc/elements/1.1/>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    SELECT DISTINCT ?celex ?date ?title
    WHERE {{
      ?work a cdm:resource_legal .
      ?work cdm:resource_legal_date_publication ?date .
      ?work dc:title ?title .
      ?work cdm:resource_legal_id_celex ?celex .
      FILTER(lang(?title) = "en")
      FILTER(?date >= "2024-01-01"^^xsd:date)
      {kf}
    }}
    ORDER BY DESC(?date) LIMIT 5
    """
    try:
        r = requests.get(endpoint, params={'query': query}, headers={'Accept': 'application/sparql-results+json'}, timeout=10)
        return r.json()['results']['bindings'] if r.status_code == 200 else []
    except: return []

# 将原有的隐藏 CSS 和 新的背景图 CSS 合并成一个函数
def set_page_bg_and_hide_elements(image_file):
    try:
        with open(image_file, "rb") as f:
            encoded_string = base64.b64encode(f.read()).decode()
        
        css = f"""
        <style>
        /* 1. 隐藏多余元素，但保留侧边栏展开按钮 */
        #MainMenu {{visibility: hidden;}}
        .stDeployButton {{display: none;}}
        footer {{visibility: hidden;}}
        
        /* 核心修复：确保侧边栏收起时的那个 '>' 按钮可见 */
        header {{
            background-color: transparent !important;
            visibility: visible !important;
        }}
        button[kind="headerNoPadding"] {{
            visibility: visible !important;
        }}

        /* 2. 背景透明处理 */
        .stApp {{
            background-color: transparent !important;
        }}
        
        /* 3. 设置背景图 */
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
        
        /* 4. 桌面端阅读区 */
        .block-container {{
            background-color: var(--background-color); 
            border-radius: 15px; 
            padding: 3rem 4rem; 
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08); 
            z-index: 1;
            max-width: 1000px; 
        }}

        /* 5. 📱 手机与平板适配 */
        @media (max-width: 768px) {{
            .block-container {{
                padding: 1.5rem 1rem !important; 
                border-radius: 8px !important; 
            }}
        }}

        /* 6. 🚀 强制正文变成加粗黑体 */
        .stMarkdown p, div[data-testid="stCaptionContainer"] p, .stAlert p {{
            font-family: "Microsoft YaHei", "SimHei", sans-serif !important;
            font-weight: bold !important;
            color: var(--text-color) !important;
        }}
        </style>
        """
        st.markdown(css, unsafe_allow_html=True)
    except FileNotFoundError:
        st.error(f"🚨 严重错误：找不到背景图片 bg.jpg")

# 调用背景渲染
set_page_bg_and_hide_elements("bg.jpg")

# ================= 🚨 修复关键：保留系统状态初始化 🚨 =================
if 'scan_result' not in st.session_state:
    st.session_state['scan_result'] = None
if 'history' not in st.session_state:
    st.session_state['history'] = []
if 'ai_memo' not in st.session_state:
    st.session_state['ai_memo'] = None

# ================= 2. 国际化与专注法域词库 =================
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
        "ai_tag_suggest": "Strategic Mitigation",
        "view_link": "View Full Text (EUR-Lex)"
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
        "ai_tag_suggest": "合规改进建议",
        "view_link": "查看全文 (EUR-Lex)"
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
        "ai_tag_suggest": "Strategische Minderung",
        "view_link": "Volltext anzeigen (EUR-Lex)"
    }
}

# ================= 3. 高级审计逻辑 (原样保留你所有的代码) =================
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
        
        # 3.1 细粒度 TDM 机器可读性探测
        ai_bots_blocked = []
        general_bots_blocked = False
        try:
            r_txt = requests.get(f"{domain}/robots.txt", timeout=5).text.lower()
            ai_bots_blocked = [b for b in ['gptbot', 'ccbot', 'anthropic-ai', 'claudebot'] if b in r_txt and 'disallow' in r_txt]
            general_bots_blocked = '*' in r_txt and 'disallow: /' in r_txt
        except: pass
        
        meta = soup.find('meta', attrs={'name': re.compile(r'tdm-reservation', re.I)})
        
        # 3.2 隐私与 ADM (自动化决策) 定向嗅探
        legal_url, legal_text = None, ""
        adm_flag = False
        weights = {'privacy':15, 'datenschutz':15, 'impressum':10, 'parking':-30}
        
        for a in soup.find_all('a', href=True):
            score = sum(v for k, v in weights.items() if k in a.get_text().lower() or k in a['href'].lower())
            if score > 10:
                legal_url = urljoin(url, a['href'])
                break 
                
        if legal_url:
            l_res = requests.get(legal_url, headers=headers, timeout=5)
            legal_text = BeautifulSoup(l_res.text, 'html.parser').get_text()[:4000]
            adm_flag = any(kw in legal_text.lower() for kw in ['automated decision', 'profiling', 'automatisierte entscheidung', '自动化决策'])

        # 3.3 评分逻辑 (锚定 EU/DE 标准)
        score = 20
        if ai_bots_blocked or meta: score += 30
        elif general_bots_blocked: score += 10 # 模糊拦截给低分
        if adm_flag: score += 15
        if legal_url: score += 35

        raw_data = {
            "url": url, 
            "tdm": {"meta": meta is not None, "ai_bots": ai_bots_blocked, "general_bots": general_bots_blocked},
            "privacy": {"policy_url": legal_url, "adm_declared": adm_flag},
            "score": score, "text": legal_text if legal_text else soup.get_text()[:3000]
        }
        return raw_data
    except Exception as e:
        st.error(f"Audit Failed: {e}")
        return None

# ================= 4. UI 布局与侧边栏动态逻辑 =================
_, lang_col = st.columns([5, 1])
with lang_col:
    lang = st.selectbox("English / 中文 / Deutsch", ["English", "中文", "Deutsch"], index=0, key="persist_lang")
t = ui_texts[lang]

# 【新插入：侧边栏自动爬取联动】
with st.sidebar:
    st.markdown(t["sidebar_title"])
    kw = None
    if st.session_state['scan_result']:
        r_now = st.session_state['scan_result']
        # 根据审计结果自动切换关键词
        kw = "Artificial Intelligence" if r_now['tdm']['ai_bots'] else "Data Protection"
        st.info(f"📍 Keyword: {kw}")
    
    # 执行自动爬取并生成直达链接
    updates = fetch_eu_legal_links(keywords=kw)
    if updates:
        for item in updates:
            with st.container(border=True):
                st.error(f"📅 {item['date']['value']}")
                st.markdown(f"**{item['title']['value']}**")
                celex_url = f"https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:{item['celex']['value']}"
                st.link_button(t["view_link"], celex_url)
    else:
        st.write("Monitoring Official Journal...")
    st.divider()
    st.info("Verified by: **Compliance Audit Agent**\n\nAcademic Project for FAU Research.")

# 核心控制台
st.markdown("<br><br>", unsafe_allow_html=True)
_, mid, _ = st.columns([1, 4, 1])
with mid:
    st.markdown(f"<h1 style='text-align:center;'>{t['title']}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align:center; color:#888888; font-size:1.1em; margin-top:-10px; margin-bottom:30px;'>{t['framework_notice']}</p>", unsafe_allow_html=True)
    
    url_input = st.text_input(t["input_label"], placeholder="https://...", key="persist_url", label_visibility="collapsed")
    if st.button(t["btn_scan"], type="primary", use_container_width=True):
        if url_input:
            result = run_academic_audit(url_input)
            if result:
                st.session_state['scan_result'] = result
                st.session_state['ai_memo'] = None 
                st.session_state['history'].insert(0, {"url": url_input, "score": result['score'], "time": datetime.datetime.now().strftime("%H:%M")})
                st.rerun()

    if st.session_state['history']:
        st.markdown(f"<div style='margin-top:20px;'><strong>{t['history_label']}</strong></div>", unsafe_allow_html=True)
        cols = st.columns(min(len(st.session_state['history']), 4))
        for i, item in enumerate(st.session_state['history'][:4]):
            with cols[i]:
                st.button(f"📊 {item['score']}pts\n{urlparse(item['url']).netloc}", key=f"hist_{i}", use_container_width=True)

# ================= 5. 深度审计结果面板 (原样保留) =================
if st.session_state['scan_result']:
    r = st.session_state['scan_result']
    st.markdown("---")
    res_l, res_r = st.columns([1, 1.5])

    with res_l:
        st.subheader(t["score_title"])
        fig = go.Figure(go.Indicator(mode="gauge+number", value=r["score"], gauge={'bar': {'color': "#1f77b4"}}))
        fig.update_layout(height=180, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)

        st.subheader(t["report_title"])
        with st.container(border=True):
            st.markdown(f"**{t['tdm_layer']}**")
            if r["tdm"]["ai_bots"]: st.success(f"{t['tdm_success']}{', '.join(r['tdm']['ai_bots'])}")
            elif r["tdm"]["general_bots"]: st.warning(f"{t['tdm_grey']}")
            else: st.error(f"{t['tdm_fail']}")
        
        with st.container(border=True):
            st.markdown(f"**{t['adm_layer']}**")
            if r["privacy"]["adm_declared"]: st.success(f"{t['adm_success']}")
            else: st.warning(f"{t['adm_fail']}")
            
        with st.container(border=True):
            st.markdown(f"**{t['gdpr_layer']}**")
            if r["privacy"]["policy_url"]: st.success(f"{t['policy_success']}[Link]({r['privacy']['policy_url']})")
            else: st.error(f"{t['policy_fail']}")

        with st.expander("💾 View Structured Data (JSON)", expanded=False):
            st.json({k: v for k, v in r.items() if k != 'text'})

    with res_r:
        st.markdown(f"#### {t['ai_header']}")
        k_col, b_col = st.columns([2, 1])
        with k_col:
            api_key = st.text_input("API Key", type="password", placeholder=t["key_placeholder"], key="persist_api_key", label_visibility="collapsed")
        with b_col:
            if st.button(t["ai_btn"], use_container_width=True):
                if not api_key: st.warning("Key needed")
                else:
                    with st.spinner("Executing Doctrinal Analysis..."):
                        try:
                            vendor, b_url, m_name = get_ai_config(api_key)
                            client = OpenAI(api_key=api_key, base_url=b_url)
                            prompt = f"""
                            Task: Conduct a legal audit for {r['url']} under the EU Acquis (AI Act Art. 53, GDPR, UrhG § 44b).
                            Data: TDM AI Block({r['tdm']['ai_bots']}), ADM Declared({r['privacy']['adm_declared']}).
                            Text snippet: {r['text'][:1500]}
                            
                            Constraints: NO self-introduction. Language: {lang}. No Chinese in EN/DE mode.
                            Structure:
                            [{t['ai_tag_status']}]: Contextualize findings under EU/DE law.
                            [{t['ai_tag_risk']}]: Highlight frictions regarding Art. 53 (TDM) or Art. 22 (ADM).
                            [{t['ai_tag_suggest']}]: Academic/Legal suggestions.
                            """
                            response = client.chat.completions.create(
                                model=m_name,
                                messages=[{"role": "system", "content": f"You are an EU legal scholar. Output strictly in {lang}."}, {"role": "user", "content": prompt}],
                                temperature=0.2
                            )
                            st.session_state['ai_memo'] = (vendor, response.choices[0].message.content)
                        except Exception as e: st.error(f"Error: {e}")
        
        if st.session_state['ai_memo']:
            vendor, content = st.session_state['ai_memo']
            st.markdown(f"**{vendor}{t['ai_analysis_title']}**")
            st.info(content)

# 页脚免责声明
st.markdown("<br><br><br>", unsafe_allow_html=True)
st.markdown(f"<hr><center><small style='opacity:0.6;'>{t['disclaimer']}</small></center>", unsafe_allow_html=True)