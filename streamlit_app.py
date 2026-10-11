import time
import pandas as pd
import streamlit as st
from PIL import Image

st.set_page_config(
    page_title="PestSearch AI",
    page_icon="🐛",
    layout="wide",
)

# --- カスタムCSS（UI改善用） ---
st.markdown("""
<style>
/* サジェストエリア全体のコンパクト化 */
.suggest-container {
    background-color: #1E1E2E;
    border-radius: 10px;
    padding: 15px;
    margin-top: 10px;
    margin-bottom: 20px;
    border: 1px solid #333;
}
/* No Imageのプレースホルダーを大きく、目立つように */
.no-image-box {
    background-color: #2D2D3D;
    height: 150px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 8px;
    margin-bottom: 10px;
    color: #888;
    font-size: 14px;
    text-align: center;
    border: 2px dashed #444;
}
/* ファイル名の表示スタイル */
.file-name-label {
    font-size: 14px;
    font-weight: 600;
    color: #E0E0E0;
    margin-bottom: 8px;
    display: block;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
/* ダウンロードボタンの幅を100%に */
.stDownloadButton button {
    width: 100%;
}
</style>
""", unsafe_allow_html=True)

# --- データベース読み込み ---
@st.cache_data
def load_database():
    try:
        return pd.read_csv("database.csv")
    except Exception as e:
        st.error(f"データベースの読み込みに失敗しました: {e}")
        return pd.DataFrame()

df_db = load_database()

# --- サイドバー ---
with st.sidebar:
    st.header("⚙️ 設定")
    if st.button("🗑️ 会話をリセット", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

st.title("🐛 害虫対策ナレッジサジェスト (PestSearch AI)")
st.caption("入力されたキーワードから関連する対策資料・マニュアルを検索します。")

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- サムネイル・資料の描画関数（UI改善版） ---
def draw_suggested_files(suggested_files):
    if suggested_files.empty:
        return
    
    # 全体を囲むコンテナ（CSS適用）
    st.markdown('<div class="suggest-container">', unsafe_allow_html=True)
    st.markdown("💡 **参考資料が見つかりました**")
    
    # 最大3列でコンパクトに配置
    cols = st.columns(min(len(suggested_files), 3))
    
    for idx, row in suggested_files.reset_index().iterrows():
        col_idx = idx % 3 
        with cols[col_idx]:
            # ファイル名を上に配置
            st.markdown(f'<span class="file-name-label" title="{row["file_name"]}">📄 {row["file_name"]}</span>', unsafe_allow_html=True)
            
            # サムネイル画像の表示（ダミー画像がない場合は大きなプレースホルダー）
            try:
                img = Image.open(row['thumbnail_path'])
                st.image(img, use_container_width=True)
            except:
                # CSSでデザインしたNo Image枠を表示
                st.markdown(f'<div class="no-image-box">プレビュー画像なし<br>(ダミー)</div>', unsafe_allow_html=True)
            
            # ダウンロードボタン
            try:
                with open(row['pdf_path'], "rb") as f:
                    st.download_button(
                        label="開く",
                        data=f,
                        file_name=row['file_name'],
                        mime="application/pdf",
                        key=f"dl_{row['id']}_{time.time()}_{idx}",
                        use_container_width=True # ボタン幅を広げる
                    )
            except:
                st.button("ファイルなし", disabled=True, key=f"dl_err_{row['id']}_{time.time()}_{idx}", use_container_width=True)
                
    st.markdown('</div>', unsafe_allow_html=True)

# --- 過去ログの描画 ---
for message in st.session_state.messages:
    avatar = "👤" if message["role"] == "user" else "🤖"
    with st.chat_message(message["role"], avatar=avatar):
        if message.get("content"):
            st.markdown(message["content"])
        if "suggested_files" in message and not message["suggested_files"].empty:
            draw_suggested_files(message["suggested_files"])

# --- チャット入力処理 ---
if prompt := st.chat_input("キーワードを入力してください（例：ゴキブリ、アリ、ユスリカ、料金）..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    suggested_files = pd.DataFrame()
    if not df_db.empty and prompt.strip():
        keywords = prompt.strip().split()
        mask = df_db['keywords'].apply(
            lambda x: any(kw.lower() in str(x).lower() for kw in keywords)
        )
        suggested_files = df_db[mask].head(4)

    if not suggested_files.empty:
        reply_content = f"「**{prompt}**」に関する検索結果を表示します。"
    else:
        reply_content = f"「**{prompt}**」に該当する資料は見つかりませんでした。（登録キーワード: ゴキブリ, アリ, ユスリカ, 料金）"

    st.session_state.messages.append({
        "role": "assistant",
        "content": reply_content,
        "suggested_files": suggested_files
    })
    st.rerun()
