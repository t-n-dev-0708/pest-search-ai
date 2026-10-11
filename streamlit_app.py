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

# 検索対象とする虫のリスト
TARGET_PESTS = ["ゴキブリ", "アリ", "ユスリカ", "ネズミ", "ハチ", "スズメバチ", "トコジラミ", "コバエ", "ショウジョウバエ", "シロアリ", "ダニ", "ノミ"]

# --- セッション状態初期化 ---
if "transcripts" not in st.session_state:
    st.session_state.transcripts = []
if "search_filename_only" not in st.session_state:
    st.session_state.search_filename_only = True  # デフォルトでON
if "grouped_results" not in st.session_state:
    st.session_state.grouped_results = {}
if "font_size" not in st.session_state:
    st.session_state.font_size = "M"
if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "ダーク" # 初期をダークモードに設定
if "api_key" not in st.session_state:
    st.session_state.api_key = ""

# --- 動的CSS設定 ---
font_sizes = {
    "S": {"base": "12px", "title": "16px", "header": "14px", "card_title": "12px", "height": "90px"},
    "M": {"base": "14px", "title": "20px", "header": "16px", "card_title": "14px", "height": "110px"},
    "L": {"base": "16px", "title": "24px", "header": "18px", "card_title": "16px", "height": "130px"}
}
fs = font_sizes[st.session_state.font_size]

if st.session_state.theme_mode == "ダーク":
    bg_body, bg_card, card_border, card_accent = "#11111B", "#1E1E2E", "#313244", "#89B4FA"
    text_color, sub_text, input_bg = "#CDD6F4", "#A6ADC8", "#181825"
    hl_bg, hl_text = "#F9E2AF", "#11111B"
else:
    bg_body, bg_card, card_border, card_accent = "#F4F6F9", "#FFFFFF", "#DEE2E6", "#007BFF"
    text_color, sub_text, input_bg = "#FFFFFF", "#6C757D", "#FFFFFF"
    hl_bg, hl_text = "#FFE066", "#000000"

st.markdown(f"""
<style>
html, body, [data-testid="stAppViewContainer"] {{
    height: 100vh; overflow: hidden; background-color: {bg_body} !important; color: {text_color} !important; font-size: {fs['base']};
}}
.main .block-container {{
    padding-top: 0.5rem !important; padding-bottom: 0.5rem !important; padding-left: 1.5rem !important; padding-right: 1.5rem !important; max-height: 98vh;
}}
[data-testid="stTextInput"] input, [data-testid="stChatInput"] textarea, [data-testid="stChatInput"] div {{
    background-color: {input_bg} !important; color: {text_color} !important; border-color: {card_border} !important;
}}
.top-header {{
    display: flex; align-items: center; padding-bottom: 4px; border-bottom: 2px solid {card_accent}; margin-bottom: 12px;
}}
.app-title {{ font-size: {fs['title']}; font-weight: 800; color: {text_color}; }}
.kw-tag-header {{ display: inline-flex; align-items: center; gap: 8px; margin-top: 8px; margin-bottom: 8px; }}
.kw-badge {{ background-color: {hl_bg}; color: {hl_text}; font-size: {fs['header']}; font-weight: 800; padding: 4px 10px; border-radius: 6px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
.kw-count {{ font-size: {fs['base']}; color: {sub_text}; font-weight: 700; }}
.indent-block {{ padding-left: 20px; margin-bottom: 16px; border-left: 3px dashed {card_border}; }}
.file-card {{
    background-color: {bg_card}; border-radius: 8px; padding: 10px; border: 1px solid {card_border}; border-left: 5px solid {card_accent};
    box-shadow: 0 4px 6px rgba(0,0,0,0.05); transition: transform 0.2s ease, box-shadow 0.2s;
}}
.file-card:hover {{ transform: translateY(-2px); box-shadow: 0 8px 15px rgba(0,0,0,0.1); }}
.no-image-box {{ background-color: {input_bg}; height: {fs['height']}; display: flex; align-items: center; justify-content: center; border-radius: 4px; color: {sub_text}; font-size: 11px; border: 1px dashed {card_border}; }}
.file-name-text {{ font-size: {fs['card_title']}; font-weight: 700; color: {text_color}; margin-bottom: 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.log-item {{ font-size: {fs['base']}; color: {text_color}; padding: 8px 10px; border-bottom: 1px solid {card_border}; line-height: 1.5; }}
.highlight-kw {{ background-color: {hl_bg}; color: {hl_text}; font-weight: 800; padding: 2px 6px; border-radius: 4px; }}
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

# 検索再計算ロジック
def recalculate_matches():
    if df_db.empty or not st.session_state.transcripts:
        st.session_state.grouped_results = {}
        return
    
    search_only_fn = st.session_state.search_filename_only
    all_transcripts_text = " ".join(st.session_state.transcripts)
    detected_pests = [pest for pest in TARGET_PESTS if pest in all_transcripts_text]

    grouped = {}
    for pest in detected_pests:
        matched_files = []
        for _, row in df_db.iterrows():
            file_name = str(row['file_name'])
            keywords_str = str(row['keywords'])
            is_match = (pest in file_name) if search_only_fn else ((pest in file_name) or (pest in keywords_str))
            
            if is_match:
                matched_files.append({"id": row['id'], "file_name": row['file_name'], "thumbnail_path": row['thumbnail_path'], "pdf_path": row['pdf_path']})
        if matched_files:
            grouped[pest] = matched_files

    st.session_state.grouped_results = grouped

def process_text_input(text):
    if not text or not text.strip():
        return
    st.session_state.transcripts.insert(0, text.strip())
    recalculate_matches()

# --- アプリヘッダー & コントロールバー ---
st.markdown('<div class="top-header"><div class="app-title">害虫検索 AI (PestSearch AI)</div></div>', unsafe_allow_html=True)

ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([5.0, 3.0, 2.0])

with ctrl_col1: 
    st.text_input("検索対象フォルダ", placeholder="参照させたいGoogleドライブのURL", label_visibility="collapsed")

with ctrl_col2:
    with st.expander("⚙️ UI設定", expanded=False):
        col_t, col_s, col_m, col_l = st.columns([1, 0.6, 0.6, 0.6])
        with col_t:
            if st.button("☀️ ライト" if st.session_state.theme_mode == "ダーク" else "🌙 ダーク", use_container_width=True):
                st.session_state.theme_mode = "ライト" if st.session_state.theme_mode == "ダーク" else "ダーク"
                st.rerun()
        with col_s:
            if st.button("S", type="primary" if st.session_state.font_size == "S" else "secondary", use_container_width=True): st.session_state.font_size = "S"; st.rerun()
        with col_m:
            if st.button("M", type="primary" if st.session_state.font_size == "M" else "secondary", use_container_width=True): st.session_state.font_size = "M"; st.rerun()
        with col_l:
            if st.button("L", type="primary" if st.session_state.font_size == "L" else "secondary", use_container_width=True): st.session_state.font_size = "L"; st.rerun()

with ctrl_col3:
    chk_val = st.checkbox("ファイル名のみ検索", value=st.session_state.search_filename_only)
    if chk_val != st.session_state.search_filename_only:
        st.session_state.search_filename_only = chk_val
        recalculate_matches()
        st.rerun()

# 音声入力URLクエリ受け取り
query_params = st.query_params
if "voice" in query_params:
    voice_text = query_params["voice"]
    st.query_params.clear()
    process_text_input(voice_text)
    st.rerun()

# 左右メインレイアウト
col_left, col_right = st.columns([7.0, 3.0])

# --- 左カラム：検出資料 ---
with col_left:
    if not st.session_state.grouped_results:
        st.markdown(f"<div style='color:{sub_text}; font-size:{fs['base']}; padding-top:40px; text-align:center;'>会話ログから虫の種類（ゴキブリ、アリ等）が検出されると、ここに該当資料が表示されます</div>", unsafe_allow_html=True)
    else:
        left_container = st.container(height=520)
        with left_container:
            for kw, files in st.session_state.grouped_results.items():
                st.markdown(f'<div class="kw-tag-header"><span class="kw-badge">{kw}</span><span class="kw-count">{len(files)}</span></div>', unsafe_allow_html=True)
                st.markdown('<div class="indent-block">', unsafe_allow_html=True)
                cols = st.columns(4)
                for idx, item in enumerate(files):
                    with cols[idx % 4]:
                        st.markdown(f'<div class="file-card" title="{item["file_name"]}"><div class="file-name-text">{item["file_name"]}</div>', unsafe_allow_html=True)
                        try:
                            img = Image.open(item['thumbnail_path'])
                            st.image(img, use_container_width=True)
                        except Exception:
                            st.markdown('<div class="no-image-box">プレビューなし</div>', unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

# --- 右カラム：会話ログ & AI修正機能 & 入力 ---
with col_right:
    st.markdown(f"<div style='font-size:{fs['header']}; font-weight:800; color:{text_color}; margin-bottom:4px;'>会話・文字起こしログ</div>", unsafe_allow_html=True)
    
    # Gemini APIキーとコントロールボタン
    st.session_state.api_key = st.text_input("Gemini APIキー", value=st.session_state.api_key, type="password", placeholder="Gemini APIキーを入力", label_visibility="collapsed")
    
    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        if st.button("🗑️ ログ消去", use_container_width=True):
            st.session_state.transcripts = []
            st.session_state.grouped_results = {}
            st.rerun()
    with btn_col2:
        if st.button("✨ AIで修正", use_container_width=True):
            if not st.session_state.api_key:
                st.warning("APIキーを入力してください")
            elif not st.session_state.transcripts:
                st.info("修正するログがありません")
            else:
                with st.spinner("AIが文脈を修正中..."):
                    try:
                        from google import genai
                        client = genai.Client(api_key=st.session_state.api_key)
                        
                        raw_text = "\n".join(st.session_state.transcripts)
                        prompt = f"""
あなたは害虫対策の専門AIです。
以下のテキストは音声認識による文字起こしですが、専門用語や虫の名前の誤認識が含まれています。
害虫駆除の文脈として自然な日本語になるよう、推測して修正してください。

【誤認識の推測例】
- スイカ → ユスリカ
- 症状 外 → ショウジョウバエ
- 風防 → 厨房
- 声帯 → 生態
- 苦情 → 駆除
- 7割 → ゴミ回り や 水回り など

修正後のテキストのみを、元の行構成と順番を維持して出力してください。不要な説明は一切出力しないでください。

【文字起こしログ】
{raw_text}
"""
                        response = client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=prompt
                        )
                        
                        corrected_text = response.text.strip()
                        new_transcripts = [t.strip() for t in corrected_text.split("\n") if t.strip()]
                        
                        st.session_state.transcripts = new_transcripts
                        recalculate_matches()
                        st.rerun()
                    except Exception as e:
                        st.error(f"APIエラー: {e}")

    log_container = st.container(height=240)
    with log_container:
        if not st.session_state.transcripts:
            st.markdown(f"<div style='color:{sub_text}; font-size:{fs['base']};'>会話ログはまだありません</div>", unsafe_allow_html=True)
        else:
            for log in st.session_state.transcripts:
                display_log = log
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
                if (transcript) {{ status.innerText = "検出: " + transcript; sendToStreamlit(transcript); }}
            }};
            recognition.onerror = (event) => {{ if (event.error !== 'no-speech') {{ status.innerText = "エラー: " + event.error; }} }};
        }}
    </script>
    """
    components.html(speech_js, height=85)

    if input_text := st.chat_input("手動でキーワードを入力..."):
        process_text_input(input_text)
        st.rerun()
