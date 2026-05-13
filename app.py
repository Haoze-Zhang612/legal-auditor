import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import plotly.graph_objects as go
from openai import OpenAI
import re
import datetime
import base64  # <--- 新增的库，用于处理图片

# ================= 1. 页面与学术状态配置 =================
st.set_page_config(page_title="TDM & GDPR Compliance Auditor", page_icon="⚖️", layout="wide")

# 将原有的隐藏 CSS 和 新的背景图 CSS 合并成一个函数
def set_page_bg_and_hide_elements(image_file):
    try:
        with open(image_file, "rb") as f:
            encoded_string = base64.b64encode(f.read()).decode()
        
        css = f"""
        <style>
        /* 1. 隐藏 Streamlit 原生元素 */
        #MainMenu {{visibility: hidden;}}
        header {{visibility: hidden;}}
        .stDeployButton {{display: none;}}
        footer {{visibility: hidden;}}
        
        /* 2. 核心修复：把 Streamlit 默认的实心背景变透明，让底层露出来 */
        .stApp {{
            background-color: transparent !important;
        }}
        
        /* 3. 设置带透明度的背景暗纹图 */
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
            opacity: 0.25; /* 推荐设置 0.25 的透明度，不会喧宾夺主 */
            z-index: -1;
            pointer-events: none;
        }}
        
        /* 4. 核心阅读区：保留一定的底色，确保审计报告文字清晰可见 */
        .block-container {{
            background-color: var(--background-color); 
            border-radius: 15px; 
            padding-top: 2rem;
            padding-bottom: 2rem;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08); 
            z-index: 1;
        }}
        </style>
        """
        st.markdown(css, unsafe_allow_html=True)
    except FileNotFoundError:
        st.error(f"🚨 严重错误：找不到背景图片 '{image_file}'。请确保已将图片上传至 GitHub 仓库，且命名为 bg.jpg（全小写）。")
        st.markdown("""
        <style>#MainMenu {visibility: hidden;} header {visibility: hidden;} .stDeployButton {display: none;} footer {visibility: hidden;}</style>
        """, unsafe_allow_html=True)
        
# ================= 2. 国际化与专注法域词库 =================
ui_texts = {
    "English": {
        "title": "⚖️ Doctrinal Legal Tech Auditor",
        "framework_notice": "⚖️ Jurisdiction: Germany (EU Acquis Applicable)",
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
        "title": "⚖️ 深度法理自动化审计系统",
        "framework_notice": "⚖️ 适用法域：德国（适用欧盟既有规则）",
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
        "title": "⚖️ Doktrinärer Legal-Tech-Auditor",
        "framework_notice": "⚖️ Rechtsrahmen: Deutschland (unter Anwendung des EU-Acquis)",
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

# ================= 3. 高级审计逻辑 (欧盟/德国专属) =================
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

# ================= 4. 交互 UI 布局 =================

_, lang_col = st.columns([5, 1])
with lang_col:
    # 默认英文，显示三语标签
    lang = st.selectbox("English / 中文 / Deutsch", ["English", "中文", "Deutsch"], index=0, key="persist_lang")
t = ui_texts[lang]

# 核心控制台
st.markdown("<br><br>", unsafe_allow_html=True)
_, mid, _ = st.columns([1, 4, 1])
with mid:
    st.markdown(f"<h1 style='text-align:center;'>{t['title']}</h1>", unsafe_allow_html=True)
    # 适用法域副标题 (极简学术风)
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

# ================= 5. 深度审计结果面板 =================
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