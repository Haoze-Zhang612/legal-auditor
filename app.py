import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import plotly.graph_objects as go
from openai import OpenAI
import re
import datetime
import base64
import ipaddress
import json
from pathlib import Path

# ================= 1. 页面与学术状态配置 =================
st.set_page_config(page_title="TDM & GDPR Compliance Auditor", page_icon=":material/gavel:", layout="wide")

def icon_img(name, size=28):
    icons = {
        "scale": """<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 48'><rect width='48' height='48' rx='10' fill='#1f77b4'/><path d='M24 10v27M14 16h20M18 16l-7 12h14l-7-12Zm12 0-7 12h14l-7-12ZM16 37h16' fill='none' stroke='white' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/></svg>""",
        "library": """<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 48'><rect width='48' height='48' rx='10' fill='#2f6f4e'/><path d='M12 16h24M14 20v16M22 20v16M30 20v16M10 38h28M24 8l15 8H9l15-8Z' fill='none' stroke='white' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/></svg>""",
        "report": """<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 48'><rect width='48' height='48' rx='10' fill='#6c5ce7'/><path d='M15 10h14l6 6v22H15V10Z' fill='none' stroke='white' stroke-width='3' stroke-linejoin='round'/><path d='M29 10v7h6M20 24h10M20 30h8' stroke='white' stroke-width='3' stroke-linecap='round'/></svg>""",
        "data": """<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 48'><rect width='48' height='48' rx='10' fill='#b85c38'/><ellipse cx='24' cy='14' rx='12' ry='5' fill='none' stroke='white' stroke-width='3'/><path d='M12 14v18c0 3 5 6 12 6s12-3 12-6V14M12 23c0 3 5 6 12 6s12-3 12-6' fill='none' stroke='white' stroke-width='3'/></svg>"""
    }
    svg = icons.get(name, icons["scale"])
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"<img src=\"data:image/svg+xml;base64,{encoded}\" width=\"{size}\" height=\"{size}\" style=\"vertical-align:-6px;margin-right:10px;border-radius:8px;\"/>"

DEFAULT_LEGAL_REFERENCES = [
    {
        "date": "2024-07-12",
        "title": "Regulation (EU) 2024/1689 (Artificial Intelligence Act)",
        "jurisdiction": "EU",
        "source": "EUR-Lex",
        "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689",
        "topics": ["AI", "Transparency"],
        "keywords": ["ai", "artificial intelligence", "ai act", "gpai", "data", "compliance"]
    },
    {
        "date": "2024-05-17",
        "title": "German UrhG § 44b - Text und Data Mining",
        "jurisdiction": "Germany",
        "source": "Gesetze im Internet",
        "url": "https://www.gesetze-im-internet.de/urhg/__44b.html",
        "topics": ["TDM", "Copyright"],
        "keywords": ["urhg", "copyright", "tdm", "text und data mining", "nutzungsvorbehalt"]
    },
    {
        "date": "2024-05-17",
        "title": "German Copyright Act (UrhG) - English translation",
        "jurisdiction": "Germany",
        "source": "Gesetze im Internet",
        "url": "https://www.gesetze-im-internet.de/englisch_urhg/englisch_urhg.html",
        "topics": ["TDM", "Copyright"],
        "keywords": ["urhg", "copyright", "tdm", "english", "text and data mining"]
    },
    {
        "date": "2024-05-17",
        "title": "Bundesdatenschutzgesetz (BDSG) - Federal Data Protection Act",
        "jurisdiction": "Germany",
        "source": "Gesetze im Internet",
        "url": "https://www.gesetze-im-internet.de/bdsg_2018/",
        "topics": ["GDPR", "Privacy"],
        "keywords": ["bdsg", "data protection", "privacy", "gdpr", "datenschutz"]
    },
    {
        "date": "2024-05-14",
        "title": "Digitale-Dienste-Gesetz (DDG)",
        "jurisdiction": "Germany",
        "source": "Gesetze im Internet",
        "url": "https://www.gesetze-im-internet.de/ddg/",
        "topics": ["Platform", "Transparency"],
        "keywords": ["ddg", "digital services", "platform", "transparency", "dsa"]
    },
    {
        "date": "2024-05-14",
        "title": "TDDDG - Datenschutz und Privatsphäre in Telekommunikation und digitalen Diensten",
        "jurisdiction": "Germany",
        "source": "Gesetze im Internet",
        "url": "https://www.gesetze-im-internet.de/ttdsg/BJNR198210021.html",
        "topics": ["Privacy", "Platform"],
        "keywords": ["tdddg", "ttdsg", "cookies", "privacy", "telecommunication", "datenschutz"]
    },
    {
        "date": "2023-12-22",
        "title": "Allgemeines Gleichbehandlungsgesetz (AGG)",
        "jurisdiction": "Germany",
        "source": "Gesetze im Internet",
        "url": "https://www.gesetze-im-internet.de/agg/",
        "topics": ["ADM", "Liability"],
        "keywords": ["agg", "discrimination", "bias", "automated decision", "employment"]
    },
    {
        "date": "2022-10-27",
        "title": "Regulation (EU) 2022/2065 (Digital Services Act)",
        "jurisdiction": "EU",
        "source": "EUR-Lex",
        "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32022R2065",
        "topics": ["Platform", "Transparency"],
        "keywords": ["dsa", "digital services", "platform", "transparency", "online platforms"]
    },
    {
        "date": "2019-05-17",
        "title": "Directive (EU) 2019/790 on copyright and related rights in the Digital Single Market",
        "jurisdiction": "EU",
        "source": "EUR-Lex",
        "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32019L0790",
        "topics": ["TDM", "Copyright"],
        "keywords": ["copyright", "tdm", "text and data mining", "data mining", "training data"]
    },
    {
        "date": "2018-12-21",
        "title": "Regulation (EU) 2018/1807 on the free flow of non-personal data",
        "jurisdiction": "EU",
        "source": "EUR-Lex",
        "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32018R1807",
        "topics": ["Data", "Platform"],
        "keywords": ["non-personal data", "data", "free flow", "data economy"]
    },
    {
        "date": "2017-07-17",
        "title": "Produkthaftungsgesetz (ProdHaftG)",
        "jurisdiction": "Germany",
        "source": "Gesetze im Internet",
        "url": "https://www.gesetze-im-internet.de/prodhaftg/",
        "topics": ["Liability"],
        "keywords": ["product liability", "liability", "prodhaftg", "ai liability", "safety"]
    },
    {
        "date": "2016-05-04",
        "title": "Regulation (EU) 2016/679 (General Data Protection Regulation)",
        "jurisdiction": "EU",
        "source": "EUR-Lex",
        "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32016R0679",
        "topics": ["GDPR", "ADM", "Privacy"],
        "keywords": ["gdpr", "data protection", "privacy", "automated decision", "profiling", "article 22"]
    }
]

@st.cache_data(ttl=3600)
def load_legal_references():
    """
    Load curated official references from JSON so the legal library can grow
    without turning the application code into a document database.
    """
    reference_path = Path(__file__).with_name("legal_references.json")
    try:
        references = json.loads(reference_path.read_text(encoding="utf-8"))
        return references or DEFAULT_LEGAL_REFERENCES
    except (OSError, json.JSONDecodeError):
        return DEFAULT_LEGAL_REFERENCES

def fetch_legal_references(limit=50, start_date="2016-01-01"):
    references = load_legal_references()
    results = []
    for item in references:
        if item["date"] < start_date:
            continue
        results.append({
            "date": {"value": item["date"]},
            "title": {"value": item["title"]},
            "jurisdiction": {"value": item["jurisdiction"]},
            "source": {"value": item["source"]},
            "url": {"value": item["url"]},
            "topics": {"value": item.get("topics", [])}
        })

    results.sort(key=lambda x: x["date"]["value"], reverse=True)
    return results[:limit]
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
            opacity: 0.25; 
            z-index: -1;
            pointer-events: none;
        }}
        
        /* 4. 💻 桌面端核心阅读区 */
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
            h1 {{ font-size: 1.8rem !important; text-align: center; }}
        }}

        /* 6. 强制语言选择器的标题单行显示 */
        div[data-testid="stSelectbox"] label p {{ white-space: nowrap !important; }}

        /* 7. 🚀 新增：强制正文、副标题变成加粗黑体 */
        .stMarkdown p, div[data-testid="stCaptionContainer"] p, .stAlert p {{
            font-family: "Microsoft YaHei", "SimHei", sans-serif !important;
            font-weight: bold !important;
            color: var(--text-color) !important;
        }}
        
        /* 8. 修复：侧边栏展开按钮可见性 */
        header {{ visibility: visible !important; background: transparent !important; }}
        button[kind="headerNoPadding"] {{ visibility: visible !important; }}
        </style>
        """
        st.markdown(css, unsafe_allow_html=True)
    except FileNotFoundError:
        st.error("Background image not found.")

# 调用渲染
set_page_bg_and_hide_elements("bg.jpg")

# ================= 系统状态初始化 =================
if 'scan_result' not in st.session_state:
    st.session_state['scan_result'] = None
if 'history' not in st.session_state:
    st.session_state['history'] = []
if 'ai_memo' not in st.session_state:
    st.session_state['ai_memo'] = None

# ================= 2. 国际化与专注法域词库 (增加侧边栏所需字段) =================
ui_texts = {
    "English": {
        "title": "Legal Tech Auditor",
        "framework_notice": "Jurisdiction: Germany (EU Acquis Applicable)",
        "input_label": "Enter Target URL",
        "btn_scan": "Run Compliance Check",
        "history_label": "Recent Audits",
        "ai_header": "Doctrinal AI Analysis",
        "ai_btn": "Generate Doctrinal Memo",
        "key_placeholder": "Paste API Key...",
        "disclaimer": "Academic Prototype for EU/DE Law Research, not Legal Advice.",
        "score_title": "Overall Compliance Score",
        "report_title": "Empirical Audit Results",
        "tdm_layer": "1. Text & Data Mining (TDM) Reservation",
        "adm_layer": "2. Automated Decision-Making (ADM)",
        "gdpr_layer": "3. Transparency & Privacy (GDPR)",
        "tdm_success": "AI crawlers blocked: ",
        "tdm_grey": "Grey area: general bot blocking found, but lacks specific AI directives.",
        "tdm_fail": "No machine-readable reservation found.",
        "adm_success": "Profiling/ADM keywords detected in policy.",
        "adm_fail": "No clear Automated Decision-Making (ADM) declarations found.",
        "policy_success": "Policy documented: ",
        "policy_fail": "Critical transparency gap: no privacy policy found.",
        "ai_analysis_title": " Analysis Results",
        "ai_tag_status": "Current Doctrinal Status",
        "ai_tag_risk": "Compliance Friction",
        "ai_tag_suggest": "Strategic Mitigation",
        "sidebar_title": "Regulatory Reference Feed",
        "view_link": "View Official Text",
        "results_found": "Found {} verified reference documents",
        "monitoring": "No matching verified reference in local baseline.",
        "verified": "Verified by: **Compliance Audit Agent**",
        "topics_label": "Topics",
        "structured_data": "View Structured Data (JSON)"
    },
    "中文": {
        "title": "自动化合规检测系统",
        "framework_notice": "适用法域：德国（适用欧盟既有规则）",
        "input_label": "输入目标网址",
        "btn_scan": "开始合规检测",
        "history_label": "最近扫描记录",
        "ai_header": "AI 法理分析",
        "ai_btn": "生成法理备忘录",
        "key_placeholder": "粘贴 API Key...",
        "disclaimer": "针对欧盟/德国法的学术研究原型，不构成正式法律建议。",
        "score_title": "综合合规得分",
        "report_title": "深度审计报告",
        "tdm_layer": "1. TDM 权利保留 (§ 44b UrhG)",
        "adm_layer": "2. 自动化决策 (ADM)",
        "gdpr_layer": "3. 透明度与隐私 (GDPR)",
        "tdm_success": "已明确拦截 AI 爬虫: ",
        "tdm_grey": "灰色地带：发现通用爬虫拦截，但缺乏针对 AI 的明确指令。",
        "tdm_fail": "未发现机器可读的 TDM 权利保留声明。",
        "adm_success": "在政策中检测到用户画像/自动化决策 (ADM) 声明。",
        "adm_fail": "未发现明确的自动化决策 (ADM) 透明度声明。",
        "policy_success": "已定位隐私政策链接: ",
        "policy_fail": "透明度风险：未发现隐私政策链接。",
        "ai_analysis_title": " 分析结果",
        "ai_tag_status": "合规现状",
        "ai_tag_risk": "核心法理摩擦",
        "ai_tag_suggest": "合规改进建议",
        "sidebar_title": "欧盟/德国法规参考源",
        "view_link": "查看官方文本",
        "results_found": "共发现 {} 份已核验参考文件",
        "monitoring": "本地核验基线中暂无匹配文件。",
        "verified": "认证系统: **合规审计 Agent**",
        "topics_label": "主题",
        "structured_data": "查看结构化数据 (JSON)"
    },
    "Deutsch": {
        "title": "Legal-Tech-Auditor",
        "framework_notice": "Rechtsrahmen: Deutschland (unter Anwendung des EU-Acquis)",
        "input_label": "Ziel-URL eingeben",
        "btn_scan": "Compliance-Prüfung starten",
        "history_label": "Letzte Prüfungen",
        "ai_header": "Doktrinäre KI-Analyse",
        "ai_btn": "Doktrinäres Memo generieren",
        "key_placeholder": "API-Key einfügen...",
        "disclaimer": "Akademischer Prototyp für die EU/DE-Rechtsforschung, keine Rechtsberatung.",
        "score_title": "Gesamt-Compliance-Score",
        "report_title": "Empirische Prüfergebnisse",
        "tdm_layer": "1. TDM-Nutzungsvorbehalt (§ 44b UrhG)",
        "adm_layer": "2. Automatisierte Entscheidungsfindung (ADM)",
        "gdpr_layer": "3. Transparenz & Datenschutz (DSGVO)",
        "tdm_success": "KI-Crawler blockiert: ",
        "tdm_grey": "Grauzone: Allgemeine Bot-Blockierung gefunden, aber keine spezifischen KI-Anweisungen.",
        "tdm_fail": "Kein maschinenlesbarer Nutzungsvorbehalt gefunden.",
        "adm_success": "Profiling/ADM-Begriffe in der Richtlinie erkannt.",
        "adm_fail": "Keine klaren Erklärungen zur Automatisierten Entscheidungsfindung (ADM) gefunden.",
        "policy_success": "Datenschutzerklärung gefunden: ",
        "policy_fail": "Transparenzrisiko: Keine Datenschutzerklärung gefunden.",
        "ai_analysis_title": " Analyseergebnis",
        "ai_tag_status": "Doktrinärer Status",
        "ai_tag_risk": "Compliance-Friktion",
        "ai_tag_suggest": "Strategische Minderung",
        "sidebar_title": "Regulierungsreferenzen",
        "view_link": "Amtlichen Text anzeigen",
        "results_found": "{} geprüfte Referenzdokumente gefunden",
        "monitoring": "Keine passende geprüfte Referenz in der lokalen Basis.",
        "verified": "Verifiziert durch: **Compliance Audit Agent**",
        "topics_label": "Themen",
        "structured_data": "Strukturierte Daten anzeigen (JSON)"
    }
}
# ================= 3. 高级审计逻辑 (无删减版) =================
def get_ai_config(key):
    if key.startswith("gsk_"): return "Groq", "https://api.groq.com/openai/v1", "llama-3.3-70b-versatile"
    if key.startswith("AIza"): return "Gemini", "https://generativelanguage.googleapis.com/v1beta/openai/", "gemini-1.5-flash"
    if "deepseek" in key.lower() or (key.startswith("sk-") and len(key) < 45): return "DeepSeek", "https://api.deepseek.com", "deepseek-chat"
    return "OpenAI", "https://api.openai.com/v1", "gpt-4o-mini"

def normalize_url(raw_url):
    url = raw_url.strip()
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("Please enter a valid HTTP(S) URL.")
    return url

def is_public_host(url):
    host = urlparse(url).hostname
    if not host:
        return False
    if host in ("localhost",):
        return False
    try:
        ip = ipaddress.ip_address(host)
        return not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved)
    except ValueError:
        return True

def site_origin(url):
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"

def normalized_domain(url):
    return urlparse(url).netloc.lower().removeprefix("www.")

def fetch_html(url, headers, timeout=10):
    if not is_public_host(url):
        raise ValueError("Private, localhost, or reserved addresses are blocked for safer auditing.")
    response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
    response.raise_for_status()
    return response.url, BeautifulSoup(response.text, 'html.parser'), response.text

def parse_robots_groups(robots_text):
    groups = []
    agents = []
    rules = []

    def flush_group():
        if agents or rules:
            groups.append({"agents": agents.copy(), "rules": rules.copy()})

    for raw_line in robots_text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue

        field, value = [part.strip() for part in line.split(":", 1)]
        field = field.lower()
        value = value.strip()

        if field == "user-agent":
            if rules:
                flush_group()
                agents, rules = [], []
            agents.append(value.lower())
        elif field in ("allow", "disallow") and agents:
            rules.append((field, value))

    flush_group()
    return groups

def path_is_full_block(path):
    normalized = path.strip().lower()
    return normalized in ("/", "/*")

def audit_robots(domain, headers):
    ai_bots = ['gptbot', 'ccbot', 'google-extended', 'anthropic-ai', 'claudebot', 'omgilibot']
    try:
        response = requests.get(f"{domain}/robots.txt", headers=headers, timeout=5)
        response.raise_for_status()
    except requests.RequestException:
        return {"ai_bots": [], "general_bots": False, "evidence": []}

    groups = parse_robots_groups(response.text)
    blocked_ai = set()
    general_bots_blocked = False
    evidence = []

    for group in groups:
        agents = group["agents"]
        full_disallows = [value for field, value in group["rules"] if field == "disallow" and path_is_full_block(value)]
        if not full_disallows:
            continue

        if "*" in agents:
            general_bots_blocked = True
            evidence.append("User-agent: * + Disallow: /")

        for bot in ai_bots:
            if bot in agents:
                blocked_ai.add(bot)
                evidence.append(f"User-agent: {bot} + Disallow: {full_disallows[0]}")

    return {
        "ai_bots": sorted(blocked_ai),
        "general_bots": general_bots_blocked,
        "evidence": evidence[:6]
    }

def detect_tdm_meta(soup):
    metas = soup.find_all('meta', attrs={'name': re.compile(r'^tdm-reservation$', re.I)})
    for meta in metas:
        content = meta.get("content", "").strip().lower()
        if content in ("1", "true", "yes"):
            return True, f'<meta name="tdm-reservation" content="{content}">'
    return False, None

def split_clauses(text):
    compact = re.sub(r"\s+", " ", text).strip().lower()
    return re.split(r"(?<=[.!?。！？;；])\s+", compact)

def detect_tdm_clause(text):
    topics = [
        "text and data mining", "tdm", "ai training", "artificial intelligence training",
        "machine learning", "training data", "data mining", "scraping", "crawler",
        "ki-training", "künstliche intelligenz", "nutzungsvorbehalt", "§ 44b", "urhg",
        "人工智能训练", "ai训练", "数据挖掘", "机器学习", "爬取", "抓取"
    ]
    restrictions = [
        "not permitted", "prohibited", "forbidden", "reserved", "opt-out",
        "without permission", "may not", "must not", "no scraping",
        "untersagt", "verboten", "vorbehalten", "nicht gestattet", "nicht erlaubt",
        "ohne zustimmung", "widerspruch",
        "禁止", "不得", "未经许可", "保留权利", "权利保留", "不同意"
    ]

    for clause in split_clauses(text):
        if any(topic in clause for topic in topics) and any(term in clause for term in restrictions):
            return True, clause[:350]
    return False, None

def find_policy_links(soup, base_url):
    base_domain = normalized_domain(base_url)
    candidates = []
    weights = {
        'privacy': 40, 'datenschutz': 40, 'data protection': 35,
        'privacypolicy': 35, 'privacy-policy': 35,
        'terms': 12, 'conditions': 12, 'legal': 10, 'impressum': 8,
        '隐私': 40, '个人信息': 35, '数据保护': 35, '条款': 10
    }

    for a_tag in soup.find_all('a', href=True):
        text = a_tag.get_text(" ", strip=True).lower()
        href = a_tag["href"].strip()
        full_url = urljoin(base_url, href)
        parsed = urlparse(full_url)
        if parsed.scheme not in ("http", "https"):
            continue
        if normalized_domain(full_url) != base_domain:
            continue

        haystack = f"{text} {href.lower()}"
        score = sum(value for keyword, value in weights.items() if keyword in haystack)
        if score > 0:
            candidates.append((score, full_url))

    candidates.sort(key=lambda item: item[0], reverse=True)
    unique_links = []
    for _, link in candidates:
        if link not in unique_links:
            unique_links.append(link)
    return unique_links[:5]

def candidate_policy_urls(base_url):
    paths = [
        "/policies/privacy-policy",
        "/privacy-policy",
        "/privacy",
        "/legal/privacy-policy",
        "/legal/privacy",
        "/privacy-notice",
        "/datenschutz",
        "/privacy/policy",
        "/policies/privacy"
    ]
    return [urljoin(base_url, path) for path in paths]

def known_verified_policy_result(base_url):
    known_policies = {
        "reddit.com": "https://www.reddit.com/policies/privacy-policy"
    }
    policy_url = known_policies.get(normalized_domain(base_url))
    if not policy_url:
        return None
    return {
        "policy_url": policy_url,
        "policy_text": "",
        "adm_declared": False,
        "adm_evidence": None,
        "tdm_clause": False,
        "tdm_evidence": None,
        "policy_discovery": "known_verified_path"
    }

def detect_adm_clause(text):
    terms = [
        "automated decision", "automated decision-making", "solely automated",
        "profiling", "article 22", "art. 22", "automatisierte entscheidung",
        "automatisierte entscheidungsfindung", "profiling", "自动化决策", "用户画像"
    ]
    for clause in split_clauses(text):
        if any(term in clause for term in terms):
            return True, clause[:350]
    return False, None

def empty_policy_result(discovery_note="not_found"):
    return {
        "policy_url": None,
        "policy_text": "",
        "adm_declared": False,
        "adm_evidence": None,
        "tdm_clause": False,
        "tdm_evidence": None,
        "policy_discovery": discovery_note
    }

def audit_policy_url(policy_url, headers, discovery_note):
    try:
        final_url, policy_soup, _ = fetch_html(policy_url, headers, timeout=6)
    except (requests.RequestException, ValueError):
        return None

    policy_text = policy_soup.get_text(" ", strip=True)
    adm_declared, adm_evidence = detect_adm_clause(policy_text)
    tdm_declared, tdm_evidence = detect_tdm_clause(policy_text)
    return {
        "policy_url": final_url,
        "policy_text": policy_text[:4000],
        "adm_declared": adm_declared,
        "adm_evidence": adm_evidence,
        "tdm_clause": tdm_declared,
        "tdm_evidence": tdm_evidence,
        "policy_discovery": discovery_note
    }

def audit_policy_pages(soup, base_url, headers):
    for policy_url in find_policy_links(soup, base_url):
        result = audit_policy_url(policy_url, headers, "page_link")
        if result:
            return result

    for policy_url in candidate_policy_urls(base_url):
        result = audit_policy_url(policy_url, headers, "fallback_path")
        if result:
            return result

    known_result = known_verified_policy_result(base_url)
    if known_result:
        return known_result

    return empty_policy_result()

def audit_policy_fallback(base_url, headers):
    for policy_url in candidate_policy_urls(base_url):
        result = audit_policy_url(policy_url, headers, "fallback_path_after_page_block")
        if result:
            return result

    known_result = known_verified_policy_result(base_url)
    if known_result:
        known_result["policy_discovery"] = "known_verified_path_after_page_block"
        return known_result

    return empty_policy_result("unconfirmed_page_blocked")

def calculate_audit_score(tdm, privacy):
    score = 0
    if tdm["meta"]:
        score += 35
    if tdm["ai_bots"]:
        score += 35
    elif tdm["general_bots"]:
        score += 10
    if tdm.get("natural_language"):
        score += 10
    if privacy["policy_url"]:
        score += 15
    if privacy["adm_declared"]:
        score += 5
    return min(score, 100)

def build_certainty(tdm, privacy, access_error=None):
    if tdm["meta"] or tdm["ai_bots"]:
        tdm_status = "Confirmed machine-readable reservation"
        tdm_level = "Confirmed"
    elif tdm["general_bots"]:
        tdm_status = "General bot block found, but AI-specific reservation not confirmed"
        tdm_level = "Likely"
    elif access_error:
        tdm_status = "Homepage blocked; only robots.txt and fallback checks were possible"
        tdm_level = "Unconfirmed"
    else:
        tdm_status = "No machine-readable TDM reservation found"
        tdm_level = "Not found"

    if privacy["policy_url"]:
        privacy_status = "Privacy policy located"
        privacy_level = "Confirmed"
    elif access_error:
        privacy_status = "Privacy policy could not be confirmed because homepage access was blocked"
        privacy_level = "Unconfirmed"
    else:
        privacy_status = "No privacy policy link found in accessible pages"
        privacy_level = "Not found"

    if privacy["adm_declared"]:
        adm_status = "ADM/profiling language detected"
        adm_level = "Confirmed"
    elif privacy["policy_url"] and privacy.get("policy_discovery", "").startswith("known_verified"):
        adm_status = "Policy link known, but policy text was not accessible for ADM analysis"
        adm_level = "Unconfirmed"
    elif privacy["policy_url"]:
        adm_status = "Policy reviewed; no ADM/profiling language detected"
        adm_level = "Not found"
    elif access_error:
        adm_status = "ADM could not be assessed because policy text was unavailable"
        adm_level = "Unconfirmed"
    else:
        adm_status = "No ADM/profiling declaration found"
        adm_level = "Not found"

    return {
        "tdm": {"level": tdm_level, "status": tdm_status},
        "privacy": {"level": privacy_level, "status": privacy_status},
        "adm": {"level": adm_level, "status": adm_status}
    }

def run_academic_audit(url):
    url = normalize_url(url)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.8,de;q=0.6',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    }
    
    try:
        final_url, soup, _ = fetch_html(url, headers, timeout=10)
        domain = site_origin(final_url)

        robots = audit_robots(domain, headers)
        meta_found, meta_evidence = detect_tdm_meta(soup)
        page_text = soup.get_text(" ", strip=True)
        page_tdm_declared, page_tdm_evidence = detect_tdm_clause(page_text)
        policy = audit_policy_pages(soup, final_url, headers)

        tdm_natural = page_tdm_declared or policy["tdm_clause"]
        tdm_evidence = page_tdm_evidence or policy["tdm_evidence"]
        tdm = {
            "meta": meta_found,
            "meta_evidence": meta_evidence,
            "ai_bots": robots["ai_bots"],
            "general_bots": robots["general_bots"],
            "robots_evidence": robots["evidence"],
            "natural_language": tdm_natural,
            "natural_language_evidence": tdm_evidence
        }
        privacy = {
            "policy_url": policy["policy_url"],
            "adm_declared": policy["adm_declared"],
            "adm_evidence": policy["adm_evidence"],
            "policy_discovery": policy["policy_discovery"]
        }
        score = calculate_audit_score(tdm, privacy)
        certainty = build_certainty(tdm, privacy)

        raw_data = {
            "url": final_url,
            "tdm": tdm,
            "privacy": privacy,
            "score": score,
            "certainty": certainty,
            "text": policy["policy_text"] if policy["policy_text"] else page_text[:3000],
            "access_error": None
        }
        return raw_data
    except requests.HTTPError as e:
        status_code = e.response.status_code if e.response is not None else "HTTP"
        domain = site_origin(url)
        robots = audit_robots(domain, headers)
        policy = audit_policy_fallback(domain, headers)
        tdm = {
            "meta": False,
            "meta_evidence": None,
            "ai_bots": robots["ai_bots"],
            "general_bots": robots["general_bots"],
            "robots_evidence": robots["evidence"],
            "natural_language": policy["tdm_clause"],
            "natural_language_evidence": policy["tdm_evidence"]
        }
        privacy = {
            "policy_url": policy["policy_url"],
            "adm_declared": policy["adm_declared"],
            "adm_evidence": policy["adm_evidence"],
            "policy_discovery": policy["policy_discovery"]
        }
        access_error = f"Target page returned {status_code}; homepage-derived checks were skipped. robots.txt and privacy fallback paths were audited."
        return {
            "url": url,
            "tdm": tdm,
            "privacy": privacy,
            "score": calculate_audit_score(tdm, privacy),
            "certainty": build_certainty(tdm, privacy, access_error=access_error),
            "text": policy["policy_text"],
            "access_error": access_error
        }
    except (requests.RequestException, ValueError) as e:
        st.error(f"Audit Failed: {e}")
        return None

# ================= 4. 交互 UI 布局 =================

_, lang_col = st.columns([6, 1])
with lang_col:
    # 移除了 horizontal=True，恢复默认的竖向排列
    lang = st.radio("Language", ["English", "中文", "Deutsch"], index=0, key="persist_lang", label_visibility="collapsed")
t = ui_texts[lang]

# --- 【新插入：侧边栏联动逻辑】 ---
with st.sidebar:
    st.markdown(
        f"<h2 style='display:flex;align-items:center;margin:0 0 0.5rem 0;'>{icon_img('library', 26)}{t['sidebar_title']}</h2>",
        unsafe_allow_html=True
    )
    st.divider()

    updates = fetch_legal_references(limit=50, start_date="2016-01-01")
    
    # 渲染结果卡片
    if updates:
        # 动态插入文件数量
        st.caption(t["results_found"].format(len(updates)))
        
        with st.container(height=500, border=False): 
            for item in updates:
                with st.container(border=True):
                    st.caption(f"{item['date']['value']} | {item['jurisdiction']['value']} | {item['source']['value']}") 
                    st.markdown(f"<p style='font-size:14px; font-weight:bold;'>{item['title']['value']}</p>", unsafe_allow_html=True)
                    if item["topics"]["value"]:
                        st.caption(f"{t['topics_label']}: " + ", ".join(item["topics"]["value"]))
                    st.markdown(f"[{t['view_link']}]({item['url']['value']})")
    else:
        st.info(t["monitoring"])
        
    st.divider()
    st.caption(t["verified"])
# 核心控制台
st.markdown("<br><br>", unsafe_allow_html=True)
_, mid, _ = st.columns([1, 4, 1])
with mid:
    st.markdown(
        f"<h1 style='text-align:center;'>{icon_img('scale', 42)}{t['title']}</h1>",
        unsafe_allow_html=True
    )
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
                st.button(f"{item['score']} pts\n{urlparse(item['url']).netloc}", key=f"hist_{i}", use_container_width=True)

# ================= 5. 深度审计结果面板 (原封不动) =================
if st.session_state['scan_result']:
    r = st.session_state['scan_result']
    st.markdown("---")
    res_l, res_r = st.columns([1, 1.5])

    with res_l:
        if r.get("access_error"):
            st.warning(r["access_error"])

        st.subheader(t["score_title"])
        fig = go.Figure(go.Indicator(mode="gauge+number", value=r["score"], gauge={'bar': {'color': "#1f77b4"}}))
        fig.update_layout(height=180, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)

        st.subheader(t["report_title"])
        with st.container(border=True):
            st.markdown(f"**{t['tdm_layer']}**")
            st.caption(f"Certainty: {r.get('certainty', {}).get('tdm', {}).get('level', 'Unknown')} - {r.get('certainty', {}).get('tdm', {}).get('status', '')}")
            if r["tdm"]["ai_bots"]: st.success(f"{t['tdm_success']}{', '.join(r['tdm']['ai_bots'])}")
            elif r["tdm"]["general_bots"]: st.warning(f"{t['tdm_grey']}")
            else: st.error(f"{t['tdm_fail']}")
            if r["tdm"].get("meta_evidence"):
                st.caption(f"Meta evidence: {r['tdm']['meta_evidence']}")
            if r["tdm"].get("robots_evidence"):
                st.caption("Robots evidence: " + " | ".join(r["tdm"]["robots_evidence"]))
            if r["tdm"].get("natural_language_evidence"):
                st.caption(f"Text evidence: {r['tdm']['natural_language_evidence']}")
        
        with st.container(border=True):
            st.markdown(f"**{t['adm_layer']}**")
            st.caption(f"Certainty: {r.get('certainty', {}).get('adm', {}).get('level', 'Unknown')} - {r.get('certainty', {}).get('adm', {}).get('status', '')}")
            if r["privacy"]["adm_declared"]: st.success(f"{t['adm_success']}")
            else: st.warning(f"{t['adm_fail']}")
            if r["privacy"].get("adm_evidence"):
                st.caption(f"ADM evidence: {r['privacy']['adm_evidence']}")
            
        with st.container(border=True):
            st.markdown(f"**{t['gdpr_layer']}**")
            st.caption(f"Certainty: {r.get('certainty', {}).get('privacy', {}).get('level', 'Unknown')} - {r.get('certainty', {}).get('privacy', {}).get('status', '')}")
            if r["privacy"]["policy_url"]:
                st.success(f"{t['policy_success']}[Link]({r['privacy']['policy_url']})")
                st.caption(f"Discovery: {r['privacy'].get('policy_discovery', 'unknown')}")
            elif r.get("access_error"):
                st.warning("Privacy policy could not be confirmed because the target homepage blocked server access.")
            else:
                st.error(f"{t['policy_fail']}")

        with st.expander(t["structured_data"], expanded=False):
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
