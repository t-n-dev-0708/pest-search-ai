import time
import re
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image

st.set_page_config(
    page_title="PestSearch AI",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- セッション状態初期化 ---
if "transcripts" not in st.session_state:
    st.session_state.transcripts = []

if "search_filename_only" not in st.session_state:
    st.session_state.search_filename_only = False

if "grouped_results" not in st.session_state:
    st.session_state.grouped_results = {}

if "font_size" not in st.session_state:
    st.session_state.font_size = "M"

if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "ダーク"

# --- 動的CSS設定（文字サイズ & ライト/ダークモード） ---
font_sizes = {
    "S": {"base": "12px", "title": "16px", "header": "13px", "card_title": "12px", "height": "100px"},
    "M": {"base": "13px", "title": "18px", "header": "14px", "card_title": "13px", "height": "110px"},
    "L": {"base": "15px", "title": "20px", "header": "16px", "card_title": "14px", "height": "120px"}
}
fs = font_sizes[st.session_state.font_size]

if st.session_state.theme_mode == "ダーク":
    bg_body = "#11111B"
    bg_card = "#1E1E2E"
    bg_sub = "#181825"
    text_color = "#CDD6F4"
    sub_text = "#A6ADC8"
    border_color = "#313244"
    hl_bg = "#F9E2AF"
    hl_text = "#11111B"
else:
    bg_body = "#F8F9FA"
    bg_card = "#FFFFFF"
    bg_sub = "#E9ECEF"
    text_color = "#212529"
    sub_text = "#6C757D"
    border_color = "#DEE2E6"
    hl_bg = "#FFE066"
    hl_text = "#000000"

st.markdown(f"""
<style>
html, body, [data-testid="stAppViewContainer"] {{
    height: 100vh;
    overflow: hidden;
    background-color: {bg_body};
    color: {text_color};
    font-size: {fs['base']};
}}

.main .block-container {{
    padding-top: 0.6rem !important;
    padding-bottom: 0.4rem !important;
    padding-left: 1.2rem !important;
    padding-right: 1.2rem !important;
    max-height: 98vh;
}}

.top-header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-bottom: 4px;
    border-bottom: 1px solid {border_color};
    margin-bottom: 6px;
}}
.app-title {{
    font-size: {fs['title']};
    font-weight: 700;
    color: {text_color};
}}

/* キーワードタグ見出し */
.kw-tag-header {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    margin-top: 6px;
    margin-bottom: 6px;
}}
.kw-badge {{
    background-color: {hl_bg};
    color: {hl_text};
    font-size: {fs['header']};
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 4px;
}}
.kw-count {{
    font-size: {fs['base']};
    color: {sub_text};
    font-weight: 600;
}}

/* インデントエリア */
.indent-block {{
    padding-left: 16px;
    margin-bottom: 12px;
    border-left: 2px solid {border_color};
}}

/* プレビューカード */
.file-card {{
    background-color: {bg_card};
    border-radius: 6px;
    padding: 8px;
    border: 1px solid {border_color};
    transition: transform 0.2s ease, border-color 0.2s;
}}
.file-card:hover {{
    transform: scale(1.02);
    border-color: #89B4FA;
}}

.no-image-box {{
    background-color: {bg_sub};
    height: {fs['height']};
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 4px;
    color: {sub_text};
    font-size: 11px;
    border: 1px dashed {border_color};
}}

.file-name-text {{
    font-size: {fs['card_title']};
    font-weight: 700;
    color: {text_color};
    margin-bottom: 4px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}}

.log-item {{
    font-size: {fs['base']};
    color: {text_color};
    padding: 5px 8px;
    border-bottom: 1px solid {border_color};
    line-height: 1.4;
}}

.highlight-kw {{
    background-color: {hl_bg};
    color: {hl_text};
    font-weight: 700;
    padding: 1px 4px;
    border-radius: 3px;
}}
</style>
""", unsafe_allow_html=True)

# --- データベース読み込み ---
@st.cache_data
def load_database():
    try:
        return pd.read_csv("database.csv")
    except Exception:
        return pd.DataFrame()

df_db = load_database()

# 全ログの再計算ロジック
def recalculate_matches():
    if df_db.empty or not st.session_state.transcripts:
        st.session_state.grouped_results = {}
        return
    
    search_only_fn = st.session_state.search_filename_only
    all_transcripts_text = " ".join(st.session_state.transcripts).lower()

    dict_keywords = set()
    for _, row in df_db.iterrows():
        for k in str(row['keywords']).split():
            if k.strip(): dict_keywords.add(k.strip())
        fn_clean = str(row['file_name']).replace('.pdf', '')
        for w in re.split(r'[_ \s\.\-]+', fn_clean):
            if len(w.strip()) >= 2: dict_keywords.add(w.strip())

    detected_keywords = [kw for kw in dict_keywords if kw.lower() in all_transcripts_text]

    grouped = {}
    for kw in detected_keywords:
        matched_files = []
        for _, row in df_db.iterrows():
            file_name = str(row['file_name'])
            keywords_str = str(row['keywords'])
            
            is_match = (kw.lower() in file_name.lower()) if search_only_fn else ((kw.lower() in file_name.lower()) or (kw.lower() in keywords_str.lower()))
            if is_match:
                matched_files.append({
                    "id": row['id'],
                    "file_name": row['file_name'],
                    "thumbnail_path": row['thumbnail_path'],
                    "pdf_path": row['pdf_path']
                })
        if matched_files:
            grouped[kw] = matched_files

    st.session_state.grouped_results = grouped

def process_text_input(text):
    if not text or not text.strip():
        return
    st.session_state.transcripts.insert(0, text.strip())
    recalculate_matches()

# --- アプリヘッダー ---
st.markdown("""
<div class="top-header">
    <div class="app-title">害虫検索 AI (PestSearch AI)</div>
</div>
""", unsafe_allow_html=True)

# --- コントロールバー（Drive URL / 設定） ---
ctrl_col1, ctrl_col2, ctrl_col3, ctrl_col4 = st.columns([4.5, 1.5, 1.5, 2.5])

with ctrl_col1:
    st.text_input("検索対象フォルダ (Google Drive URL)", placeholder="https://drive.google.com/drive/folders/...", label_visibility="collapsed")

with ctrl_col2:
    st.session_state.theme_mode = st.selectbox("表示モード", ["ダーク", "ライト"], index=0 if st.session_state.theme_mode == "ダーク" else 1, label_visibility="collapsed")

with ctrl_col3:
    st.session_state.font_size = st.selectbox("文字サイズ", ["S", "M", "L"], index=["S", "M", "L"].index(st.session_state.font_size), label_visibility="collapsed")

with ctrl_col4:
    chk_val = st.checkbox("ファイル名のみ検索", value=st.session_state.search_filename_only)
    if chk_val != st.session_state.search_filename_only:
        st.session_state.search_filename_only = chk_val
        recalculate_matches()
        st.rerun()

# URLクエリ受け取り
query_params = st.query_params
if "voice" in query_params:
    voice_text = query_params["voice"]
    st.query_params.clear()
    process_text_input(voice_text)
    st.rerun()

# 左右メインレイアウト
col_left, col_right = st.columns([7.2, 2.8])

# --- 左カラム：検出資料（シンプル化見出し＋インデント） ---
with col_left:
    if not st.session_state.grouped_results:
        st.markdown(f"<div style='color:{sub_text}; font-size:{fs['base']}; padding-top:40px; text-align:center;'>会話ログからキーワードが検出されると、ここに該当資料が表示されます</div>", unsafe_allow_html=True)
    else:
        left_container = st.container(height=500)
        with left_container:
            for kw, files in st.session_state.grouped_results.items():
                # シンプル見出し（例：[ゴキブリ] 2）
                st.markdown(f'''
                <div class="kw-tag-header">
                    <span class="kw-badge">{kw}</span>
                    <span class="kw-count">{len(files)}</span>
                </div>
                ''', unsafe_allow_html=True)
                
                # インデントブロック
                st.markdown('<div class="indent-block">', unsafe_allow_html=True)
                cols = st.columns(4)
                for idx, item in enumerate(files):
                    with cols[idx % 4]:
                        card_html = f'''
                        <div class="file-card" title="{item['file_name']}">
                            <div class="file-name-text">{item['file_name']}</div>
                        '''
                        st.markdown(card_html, unsafe_allow_html=True)
                        try:
                            img = Image.open(item['thumbnail_path'])
                            st.image(img, use_container_width=True)
                        except Exception:
                            st.markdown('<div class="no-image-box">プレビューなし</div>', unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

# --- 右カラム：会話ログ ＆ 常時音声認識 / 手動入力 ---
with col_right:
    st.markdown(f"<div style='font-size:{fs['header']}; font-weight:700; color:{text_color}; margin-bottom:4px;'>会話・文字起こしログ</div>", unsafe_allow_html=True)
    
    if st.button("ログを全消去", use_container_width=True):
        st.session_state.transcripts = []
        st.session_state.grouped_results = {}
        st.rerun()

    # ハイライト用キーワードの作成
    all_registered_kws = set()
    if not df_db.empty:
        for kws in df_db['keywords'].dropna():
            for k in str(kws).split():
                if k.strip(): all_registered_kws.add(k.strip())
        for fn in df_db['file_name'].dropna():
            fn_clean = str(fn).replace('.pdf', '')
            for k in re.split(r'[_ \s]+', fn_clean):
                if len(k.strip()) >= 2: all_registered_kws.add(k.strip())

    log_container = st.container(height=300)
    with log_container:
        if not st.session_state.transcripts:
            st.markdown(f"<div style='color:{sub_text}; font-size:{fs['base']};'>会話ログはまだありません</div>", unsafe_allow_html=True)
        else:
            for log in st.session_state.transcripts:
                display_log = log
                for kw in all_registered_kws:
                    if kw.lower() in display_log.lower():
                        pattern = re.compile(re.escape(kw), re.IGNORECASE)
                        display_log = pattern.sub(f'<span class="highlight-kw">{kw}</span>', display_log)
                st.markdown(f'<div class="log-item">▶ {display_log}</div>', unsafe_allow_html=True)

    # 音声認識 Web Speech API (自動送信)
    speech_js = f"""
    <div style="font-family: sans-serif; background: transparent;">
        <button id="mic-btn" style="width: 100%; padding: 8px; background-color: {bg_card}; color: #89B4FA; border: 1px solid {border_color}; border-radius: 6px; font-size: {fs['base']}; font-weight: 700; cursor: pointer;">
            🎙️ 音声聞き取りを開始する
        </button>
        <div id="mic-status" style="color: {sub_text}; font-size: 11px; margin-top: 4px; text-align: center;">ボタンを押すとマイクで連続自動認識を開始します</div>
    </div>

    <script>
        const btn = document.getElementById('mic-btn');
        const status = document.getElementById('mic-status');
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

        function sendToStreamlit(text) {{
            if (!text) return;
            try {{
                const parentDoc = window.parent.document;
                const textarea = parentDoc.querySelector('textarea[data-testid="stChatInputTextArea"]');
                if (textarea) {{
                    const nativeSetter = Object.getOwnPropertyDescriptor(window.parent.HTMLTextAreaElement.prototype, 'value').set;
                    nativeSetter.call(textarea, text);
                    textarea.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    setTimeout(() => {{
                        const sendBtn = parentDoc.querySelector('button[data-testid="stChatInputSubmitButton"]');
                        if (sendBtn) {{
                            sendBtn.click();
                        }} else {{
                            textarea.dispatchEvent(new KeyboardEvent('keydown', {{ key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true }}));
                        }}
                    }}, 100);
                    return;
                }}
            }} catch (e) {{ console.log(e); }}
            
            const targetUrl = window.parent.location.pathname + '?voice=' + encodeURIComponent(text);
            window.parent.location.href = targetUrl;
        }}

        if (!SpeechRecognition) {{
            status.innerText = "※お使いのブラウザは音声認識に対応していません";
            btn.disabled = true;
            btn.style.opacity = "0.5";
        }} else {{
            const recognition = new SpeechRecognition();
            recognition.lang = 'ja-JP';
            recognition.continuous = true;
            recognition.interimResults = false;
            
            let isUserActive = false;

            btn.onclick = () => {{
                if (isUserActive) {{
                    isUserActive = false;
                    recognition.stop();
                    btn.innerText = "🎙️ 音声聞き取りを開始する";
                    btn.style.backgroundColor = "{bg_card}";
                    btn.style.color = "#89B4FA";
                    status.innerText = "音声認識を停止しました";
                }} else {{
                    isUserActive = true;
                    try {{ recognition.start(); }} catch(e){{}}
                    btn.innerText = "🔴 聞き取り中... (クリックで停止)";
                    btn.style.backgroundColor = "#F38BA8";
                    btn.style.color = "#11111B";
                    status.innerText = "会話を常時聞き取り中...";
                }}
            }};

            recognition.onend = () => {{
                if (isUserActive) {{
                    try {{ recognition.start(); }} catch(e){{}}
                }}
            }};

            recognition.onresult = (event) => {{
                const lastIndex = event.results.length - 1;
                const transcript = event.results[lastIndex][0].transcript.trim();
                if (transcript) {{
                    status.innerText = "検出: " + transcript;
                    sendToStreamlit(transcript);
                }}
            }};

            recognition.onerror = (event) => {{
                if (event.error !== 'no-speech') {{
                    status.innerText = "エラー: " + event.error;
                }}
            }};
        }}
    </script>
    """
    components.html(speech_js, height=65)

    if input_text := st.chat_input("手動でキーワードを入力..."):
        process_text_input(input_text)
        st.rerun()
