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

# 検索対象とする虫のリスト（これ以外の単語ではグループ化しない）
TARGET_PESTS = ["ゴキブリ", "アリ", "ユスリカ", "ネズミ", "ハチ", "スズメバチ", "トコジラミ", "コバエ", "ショウジョウバエ", "シロアリ", "ダニ", "ノミ"]

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
    st.session_state.theme_mode = "ライト" # 初期をライトに

# --- 動的CSS設定（テーマ・サイズ完全上書き） ---
font_sizes = {
    "S": {"base": "12px", "title": "16px", "header": "14px", "card_title": "12px", "height": "90px"},
    "M": {"base": "14px", "title": "20px", "header": "16px", "card_title": "14px", "height": "110px"},
    "L": {"base": "16px", "title": "24px", "header": "18px", "card_title": "16px", "height": "130px"}
}
fs = font_sizes[st.session_state.font_size]

if st.session_state.theme_mode == "ダーク":
    bg_body = "#11111B"         # 全体背景
    bg_card = "#1E1E2E"         # カード背景（色付け）
    card_border = "#313244"
    card_accent = "#89B4FA"     # カード左端のアクセントカラー
    text_color = "#CDD6F4"
    sub_text = "#A6ADC8"
    input_bg = "#181825"        # 入力欄の背景
    hl_bg = "#F9E2AF"           # ハイライト黄
    hl_text = "#11111B"
else:
    bg_body = "#F4F6F9"         # 全体背景（少しグレーがかった白）
    bg_card = "#FFFFFF"         # カード背景（白）
    card_border = "#DEE2E6"
    card_accent = "#007BFF"     # カード左端のアクセントカラー
    text_color = "#212529"
    sub_text = "#6C757D"
    input_bg = "#FFFFFF"        # 入力欄の背景
    hl_bg = "#FFE066"           # ハイライト黄
    hl_text = "#000000"

st.markdown(f"""
<style>
/* 画面全体の縦スクロールを抑止 */
html, body, [data-testid="stAppViewContainer"] {{
    height: 100vh;
    overflow: hidden;
    background-color: {bg_body} !important;
    color: {text_color} !important;
    font-size: {fs['base']};
}}

.main .block-container {{
    padding-top: 0.5rem !important;
    padding-bottom: 0.5rem !important;
    padding-left: 1.5rem !important;
    padding-right: 1.5rem !important;
    max-height: 98vh;
}}

/* Streamlitネイティブウィジェットの強制色上書き */
[data-testid="stTextInput"] input, 
[data-testid="stChatInput"] textarea,
[data-testid="stChatInput"] div {{
    background-color: {input_bg} !important;
    color: {text_color} !important;
    border-color: {card_border} !important;
}}

.top-header {{
    display: flex;
    align-items: center;
    padding-bottom: 4px;
    border-bottom: 2px solid {card_accent};
    margin-bottom: 12px;
}}
.app-title {{
    font-size: {fs['title']};
    font-weight: 800;
    color: {text_color};
}}

/* キーワードタグ見出し */
.kw-tag-header {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    margin-top: 8px;
    margin-bottom: 8px;
}}
.kw-badge {{
    background-color: {hl_bg};
    color: {hl_text};
    font-size: {fs['header']};
    font-weight: 800;
    padding: 4px 10px;
    border-radius: 6px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}}
.kw-count {{
    font-size: {fs['base']};
    color: {sub_text};
    font-weight: 700;
}}

/* インデントエリア */
.indent-block {{
    padding-left: 20px;
    margin-bottom: 16px;
    border-left: 3px dashed {card_border};
}}

/* プレビューカード（色付き・アクセントライン） */
.file-card {{
    background-color: {bg_card};
    border-radius: 8px;
    padding: 10px;
    border: 1px solid {card_border};
    border-left: 5px solid {card_accent};
    box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    transition: transform 0.2s ease, box-shadow 0.2s;
}}
.file-card:hover {{
    transform: translateY(-2px);
    box-shadow: 0 8px 15px rgba(0,0,0,0.1);
}}

.no-image-box {{
    background-color: {input_bg};
    height: {fs['height']};
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 4px;
    color: {sub_text};
    font-size: 11px;
    border: 1px dashed {card_border};
}}

.file-name-text {{
    font-size: {fs['card_title']};
    font-weight: 700;
    color: {text_color};
    margin-bottom: 6px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}}

.log-item {{
    font-size: {fs['base']};
    color: {text_color};
    padding: 8px 10px;
    border-bottom: 1px solid {card_border};
    line-height: 1.5;
}}

.highlight-kw {{
    background-color: {hl_bg};
    color: {hl_text};
    font-weight: 800;
    padding: 2px 6px;
    border-radius: 4px;
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

# 全ログの再計算ロジック（虫の種類のみで判定）
def recalculate_matches():
    if df_db.empty or not st.session_state.transcripts:
        st.session_state.grouped_results = {}
        return
    
    search_only_fn = st.session_state.search_filename_only
    all_transcripts_text = " ".join(st.session_state.transcripts)

    # ログ内に TARGET_PESTS の虫が含まれているか判定
    detected_pests = [pest for pest in TARGET_PESTS if pest in all_transcripts_text]

    grouped = {}
    for pest in detected_pests:
        matched_files = []
        for _, row in df_db.iterrows():
            file_name = str(row['file_name'])
            keywords_str = str(row['keywords'])
            
            # その虫の名前がファイル名（またはキーワード）に含まれるか
            is_match = (pest in file_name) if search_only_fn else ((pest in file_name) or (pest in keywords_str))
            
            if is_match:
                matched_files.append({
                    "id": row['id'],
                    "file_name": row['file_name'],
                    "thumbnail_path": row['thumbnail_path'],
                    "pdf_path": row['pdf_path']
                })
        if matched_files:
            grouped[pest] = matched_files

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

# --- コントロールバー（Drive URL / テーマ / SMLボタン / オプション） ---
ctrl_col1, ctrl_col2, col_s, col_m, col_l, ctrl_col4 = st.columns([4.0, 0.8, 0.4, 0.4, 0.4, 2.0])

with ctrl_col1:
    st.text_input("検索対象フォルダ (Google Drive URL)", placeholder="https://drive.google.com/drive/folders/...", label_visibility="collapsed")

with ctrl_col2:
    theme_icon = "☀️ ライト" if st.session_state.theme_mode == "ダーク" else "🌙 ダーク"
    if st.button(theme_icon, use_container_width=True):
        st.session_state.theme_mode = "ライト" if st.session_state.theme_mode == "ダーク" else "ダーク"
        st.rerun()

with col_s:
    if st.button("S", type="primary" if st.session_state.font_size == "S" else "secondary", use_container_width=True):
        st.session_state.font_size = "S"
        st.rerun()
with col_m:
    if st.button("M", type="primary" if st.session_state.font_size == "M" else "secondary", use_container_width=True):
        st.session_state.font_size = "M"
        st.rerun()
with col_l:
    if st.button("L", type="primary" if st.session_state.font_size == "L" else "secondary", use_container_width=True):
        st.session_state.font_size = "L"
        st.rerun()

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
col_left, col_right = st.columns([7.0, 3.0])

# --- 左カラム：検出資料（虫の種類のみ） ---
with col_left:
    if not st.session_state.grouped_results:
        st.markdown(f"<div style='color:{sub_text}; font-size:{fs['base']}; padding-top:40px; text-align:center;'>会話ログから虫の種類（ゴキブリ、アリ等）が検出されると、ここに該当資料が表示されます</div>", unsafe_allow_html=True)
    else:
        left_container = st.container(height=520)
        with left_container:
            for kw, files in st.session_state.grouped_results.items():
                st.markdown(f'''
                <div class="kw-tag-header">
                    <span class="kw-badge">{kw}</span>
                    <span class="kw-count">{len(files)}</span>
                </div>
                ''', unsafe_allow_html=True)
                
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

# --- 右カラム：会話ログ ＆ 音声/手動入力 ---
with col_right:
    st.markdown(f"<div style='font-size:{fs['header']}; font-weight:800; color:{text_color}; margin-bottom:8px;'>会話・文字起こしログ</div>", unsafe_allow_html=True)
    
    if st.button("ログを全消去", use_container_width=True):
        st.session_state.transcripts = []
        st.session_state.grouped_results = {}
        st.rerun()

    log_container = st.container(height=320)
    with log_container:
        if not st.session_state.transcripts:
            st.markdown(f"<div style='color:{sub_text}; font-size:{fs['base']};'>会話ログはまだありません</div>", unsafe_allow_html=True)
        else:
            for log in st.session_state.transcripts:
                display_log = log
                # TARGET_PESTSの虫の名前のみハイライト
                for pest in TARGET_PESTS:
                    if pest in display_log:
                        pattern = re.compile(re.escape(pest))
                        display_log = pattern.sub(f'<span class="highlight-kw">{pest}</span>', display_log)
                st.markdown(f'<div class="log-item">▶ {display_log}</div>', unsafe_allow_html=True)

    # 音声認識 Web Speech API
    speech_js = f"""
    <div style="font-family: sans-serif; background: transparent; margin-top: 10px;">
        <button id="mic-btn" style="width: 100%; padding: 10px; background-color: {card_accent}; color: #FFF; border: none; border-radius: 6px; font-size: {fs['base']}; font-weight: 700; cursor: pointer; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            🎙️ 音声聞き取りを開始する
        </button>
        <div id="mic-status" style="color: {sub_text}; font-size: 11px; margin-top: 6px; text-align: center;">ボタンを押すとマイクで連続自動認識を開始します</div>
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
                        if (sendBtn) {{ sendBtn.click(); }} 
                        else {{ textarea.dispatchEvent(new KeyboardEvent('keydown', {{ key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true }})); }}
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
                    btn.innerHTML = "🎙️ 音声聞き取りを開始する";
                    btn.style.backgroundColor = "{card_accent}";
                    status.innerText = "音声認識を停止しました";
                }} else {{
                    isUserActive = true;
                    try {{ recognition.start(); }} catch(e){{}}
                    btn.innerHTML = "🔴 聞き取り中... (クリックで停止)";
                    btn.style.backgroundColor = "#dc3545";
                    status.innerText = "会話を常時聞き取り中...";
                }}
            }};

            recognition.onend = () => {{ if (isUserActive) {{ try {{ recognition.start(); }} catch(e){{}} }} }};
            recognition.onresult = (event) => {{
                const lastIndex = event.results.length - 1;
                const transcript = event.results[lastIndex][0].transcript.trim();
                if (transcript) {{
                    status.innerText = "検出: " + transcript;
                    sendToStreamlit(transcript);
                }}
            }};
            recognition.onerror = (event) => {{ if (event.error !== 'no-speech') {{ status.innerText = "エラー: " + event.error; }} }};
        }}
    </script>
    """
    components.html(speech_js, height=85)

    if input_text := st.chat_input("手動でキーワードを入力..."):
        process_text_input(input_text)
        st.rerun()
