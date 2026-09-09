import json
import streamlit as st
from google import genai
from PIL import Image

# Sayfa Yapılandırması
st.set_page_config(page_title="AI Diyetisyen & Makro Takibi", layout="wide")

# Session State Hazırlığı
if "current_intake" not in st.session_state:
    st.session_state.current_intake = {
        "calories": 0,
        "protein": 0,
        "carbs": 0,
        "fat": 0,
    }

if "history" not in st.session_state:
    st.session_state.history = []

# API Anahtarı Girişi
st.sidebar.title("⚙️ Ayarlar")
api_key = st.sidebar.text_input(
    "Gemini API Key Giriniz",
    type="password",
    help="aistudio.google.com adresi üzerinden ücretsiz alabilirsiniz.",
)

st.title("🥗 AI Diyetisyen & Makro Takipçisi")

# SOL KOLON: Profil ve Hesaplama
col_left, col_right = st.columns([1, 2])

with col_left:
    st.header("👤 Profil Bilgileri")
    age = st.number_input("Yaş", min_value=10, max_value=100, value=25)
    gender = st.selectbox("Cinsiyet", ["Erkek", "Kadın"])
    height = st.number_input("Boy (cm)", min_value=100, max_value=230, value=175)
    weight = st.number_input("Kilo (kg)", min_value=30, max_value=200, value=70)

    activity_mult = {
        "Hareketsiz (Masa başı)": 1.2,
        "Az Hareketli (1-3 gün spor)": 1.375,
        "Orta Hareketli (3-5 gün spor)": 1.55,
        "Çok Hareketli (6-7 gün spor)": 1.725,
    }[
        st.selectbox(
            "Aktivite Seviyesi",
            [
                "Hareketsiz (Masa başı)",
                "Az Hareketli (1-3 gün spor)",
                "Orta Hareketli (3-5 gün spor)",
                "Çok Hareketli (6-7 gün spor)",
            ],
            index=1,
        )
    ]

    goal_adj = {
        "Kilo Vermek (-500 kcal)": -500,
        "Kilo Korumak": 0,
        "Kilo Almak (+500 kcal)": 500,
    }[
        st.selectbox(
            "Hedef",
            ["Kilo Vermek (-500 kcal)", "Kilo Korumak", "Kilo Almak (+500 kcal)"],
            index=1,
        )
    ]

    # BMR & TDEE Hesabı
    bmr = (10 * weight) + (6.25 * height) - (5 * age) + (5 if gender == "Erkek" else -161)
    target_cal = int((bmr * activity_mult) + goal_adj)

    target_p = int((target_cal * 0.30) / 4)
    target_c = int((target_cal * 0.45) / 4)
    target_f = int((target_cal * 0.25) / 9)

    st.success(f"🎯 **Günlük Kalori Hedefi:** {target_cal} kcal")

# SAĞ KOLON: Makro Göstergeleri ve Yapay Zeka Analizi
with col_right:
    st.header("📊 Günlük Makro Durumu")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        "Kalori",
        f"{st.session_state.current_intake['calories']} / {target_cal} kcal",
    )
    c2.metric(
        "Protein", f"{st.session_state.current_intake['protein']}g / {target_p}g"
    )
    c3.metric(
        "Karbonhidrat",
        f"{st.session_state.current_intake['carbs']}g / {target_c}g",
    )
    c4.metric("Yağ", f"{st.session_state.current_intake['fat']}g / {target_f}g")

    st.progress(
        min(st.session_state.current_intake["calories"] / max(target_cal, 1), 1.0)
    )

    st.divider()

    st.header("📸 Öğün Fotoğrafı Analizi")
    uploaded_file = st.file_uploader(
        "Yemeğinizin fotoğrafını yükleyin...", type=["jpg", "jpeg", "png", "webp"]
    )

    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="Yüklenen Öğün", width=300)

        if st.button("🤖 Yapay Zeka İle Analiz Et"):
            if not api_key:
                st.error("Lütfen sol menüden Gemini API Key giriniz!")
            else:
                with st.spinner(
                    "Görsel analiz ediliyor ve makro değerleri hesaplanıyor..."
                ):
                    try:
                        client = genai.Client(api_key=api_key)

                        prompt = """
                        Bu görseldeki yiyeceği/öğünü analiz et.
                        Porsiyon miktarını tahmin et ve besin değerlerini hesapla.
                        Yanıtı SADECE aşağıdaki JSON formatında ver, başka hiçbir açıklama yazma:
                        {
                            "meal_name": "Yemeğin adı/açıklaması",
                            "calories": 450,
                            "protein": 35,
                            "carbs": 40,
                            "fat": 15
                        }
                        """

                        response = client.models.generate_content(
                            model="gemini-1.5-flash", contents=[image, prompt]
                        )

                        raw_json = (
                            response.text.replace("```json", "")
                            .replace("```", "")
                            .strip()
                        )
                        meal_data = json.loads(raw_json)

                        st.session_state.current_intake[
                            "calories"
                        ] += meal_data["calories"]
                        st.session_state.current_intake["protein"] += meal_data[
                            "protein"
                        ]
                        st.session_state.current_intake["carbs"] += meal_data[
                            "carbs"
                        ]
                        st.session_state.current_intake["fat"] += meal_data[
                            "fat"
                        ]

                        st.session_state.history.append(meal_data)

                        st.success(
                            f"✅ **Tespit Edilen:** {meal_data['meal_name']}"
                        )
                        st.info(
                            f"**Eklendi:** +{meal_data['calories']} kcal | +{meal_data['protein']}g Protein | +{meal_data['carbs']}g Karbonhidrat | +{meal_data['fat']}g Yağ"
                        )
                        st.rerun()

                    except Exception as e:
                        st.error(f"Analiz sırasında bir hata oluştu: {str(e)}")

    if st.session_state.history:
        st.subheader("📝 Bugün Eklenen Öğünler")
        for item in st.session_state.history:
            st.write(
                f"- **{item['meal_name']}**: {item['calories']} kcal (P: {item['protein']}g, K: {item['carbs']}g, Y: {item['fat']}g)"
            )