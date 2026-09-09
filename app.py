import streamlit as st
from google import genai
from PIL import Image
import sqlite3
import datetime
import json

# --- VERİTABANI KURULUMU VE YÖNETİMİ ---
def init_db():
    conn = sqlite3.connect("diyet_takip.db")
    c = conn.cursor()
    # Kullanıcı profili tablosu
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_profile (
            id INTEGER PRIMARY KEY,
            age INTEGER,
            gender TEXT,
            height REAL,
            weight REAL,
            activity TEXT,
            goal TEXT
        )
    ''')
    # Yemek geçmişi tablosu
    c.execute('''
        CREATE TABLE IF NOT EXISTS food_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            food_name TEXT,
            calories REAL,
            protein REAL,
            carbs REAL,
            fat REAL
        )
    ''')
    conn.commit()
    conn.close()

def load_profile():
    conn = sqlite3.connect("diyet_takip.db")
    c = conn.cursor()
    c.execute("SELECT age, gender, height, weight, activity, goal FROM user_profile WHERE id = 1")
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "age": row[0], "gender": row[1], "height": row[2],
            "weight": row[3], "activity": row[4], "goal": row[5]
        }
    return None

def save_profile(age, gender, height, weight, activity, goal):
    conn = sqlite3.connect("diyet_takip.db")
    c = conn.cursor()
    c.execute('''
        INSERT INTO user_profile (id, age, gender, height, weight, activity, goal)
        VALUES (1, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            age=excluded.age, gender=excluded.gender, height=excluded.height,
            weight=excluded.weight, activity=excluded.activity, goal=excluded.goal
    ''', (age, gender, height, weight, activity, goal))
    conn.commit()
    conn.close()

def add_food_log(food_name, calories, protein, carbs, fat):
    today = str(datetime.date.today())
    conn = sqlite3.connect("diyet_takip.db")
    c = conn.cursor()
    c.execute('''
        INSERT INTO food_logs (date, food_name, calories, protein, carbs, fat)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (today, food_name, calories, protein, carbs, fat))
    conn.commit()
    conn.close()

def load_today_logs():
    today = str(datetime.date.today())
    conn = sqlite3.connect("diyet_takip.db")
    c = conn.cursor()
    c.execute("SELECT food_name, calories, protein, carbs, fat FROM food_logs WHERE date = ?", (today,))
    rows = c.fetchall()
    conn.close()
    return rows

def clear_today_logs():
    today = str(datetime.date.today())
    conn = sqlite3.connect("diyet_takip.db")
    c = conn.cursor()
    c.execute("DELETE FROM food_logs WHERE date = ?", (today,))
    conn.commit()
    conn.close()

# Veritabanını başlat
init_db()

# --- STREAMLIT ARAYÜZÜ ---
st.set_page_config(page_title="AI Diyet & Beslenme Takibi", page_icon="🥗", layout="wide")
st.title("🥗 Yapay Zeka Destekli Kalori ve Makro Takibi")

# API Key Kontrolü (Secrets veya Yan Menü)
api_key = st.secrets.get("GEMINI_API_KEY", "")
if not api_key:
    api_key = st.sidebar.text_input("Gemini API Key Giriniz", type="password")

# Profil Verilerini Yükle
saved_profile = load_profile()

# --- YAN MENÜ: PROFİL BİLGİLERİ ---
st.sidebar.header("📊 Profil ve Metrikler")

default_age = saved_profile["age"] if saved_profile else 25
default_gender = saved_profile["gender"] if saved_profile else "Erkek"
default_height = saved_profile["height"] if saved_profile else 175.0
default_weight = saved_profile["weight"] if saved_profile else 70.0
default_activity = saved_profile["activity"] if saved_profile else "Orta Hareketli"
default_goal = saved_profile["goal"] if saved_profile else "Kilo Koru"

gender = st.sidebar.radio("Cinsiyet", ["Erkek", "Kadın"], index=0 if default_gender == "Erkek" else 1)
age = st.sidebar.number_input("Yaş", min_value=10, max_value=100, value=default_age)
height = st.sidebar.number_input("Boy (cm)", min_value=100.0, max_value=250.0, value=default_height)
weight = st.sidebar.number_input("Kilo (kg)", min_value=30.0, max_value=250.0, value=default_weight)

activity_options = ["Hareketsiz", "Az Hareketli", "Orta Hareketli", "Çok Hareketli"]
activity_idx = activity_options.index(default_activity) if default_activity in activity_options else 2
activity = st.sidebar.selectbox("Aktivite Seviyesi", activity_options, index=activity_idx)

goal_options = ["Kilo Ver", "Kilo Koru", "Kilo Al"]
goal_idx = goal_options.index(default_goal) if default_goal in goal_options else 1
goal = st.sidebar.selectbox("Hedef", goal_options, index=goal_idx)

# Profil Bilgilerini Kaydet Butonu
if st.sidebar.button("Profil Bilgilerini Kaydet"):
    save_profile(age, gender, height, weight, activity, goal)
    st.sidebar.success("Profil kaydedildi!")

# --- METABOLİZMA HESAPLAMA (Mifflin-St Jeor) ---
if gender == "Erkek":
    bmr = 10 * weight + 6.25 * height - 5 * age + 5
else:
    bmr = 10 * weight + 6.25 * height - 5 * age - 161

activity_multipliers = {
    "Hareketsiz": 1.2,
    "Az Hareketli": 1.375,
    "Orta Hareketli": 1.55,
    "Çok Hareketli": 1.725
}
tdee = bmr * activity_multipliers.get(activity, 1.55)

if goal == "Kilo Ver":
    target_calories = tdee - 500
elif goal == "Kilo Al":
    target_calories = tdee + 500
else:
    target_calories = tdee

# --- ANA EKRAN ---
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📸 Öğün Yükle & Analiz Et")
    uploaded_file = st.file_uploader("Bir yemek fotoğrafı seçin veya çekin...", type=["jpg", "jpeg", "png"])
    
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="Yüklenen Öğün", use_column_width=True)
        
        if st.button("Yapay Zeka İle Analiz Et"):
            if not api_key:
                st.error("Lütfen bir Gemini API Key giriniz!")
            else:
                with st.spinner("Yemek analiz ediliyor..."):
                    try:
                        client = genai.Client(api_key=api_key)
                        prompt = """
                        Bu bir yemek fotoğrafıdır. Görseldeki yiyecekleri tespit et, tahmini porsiyon miktarını belirle ve toplam besin değerlerini hesapla.
                        Yanıtı SADECE geçerli bir JSON formatında ver. Başka hiçbir açıklama yazma.
                        JSON formatı tam olarak şöyle olmalıdır:
                        {
                            "food_name": "Yemeğin Adı ve Kısa Açıklaması",
                            "calories": 450,
                            "protein": 30,
                            "carbs": 40,
                            "fat": 15
                        }
                        """
                        response = client.models.generate_content(
                            model="gemini-1.5-flash",
                            contents=[image, prompt]
                        )
                        
                        clean_text = response.text.replace("```json", "").replace("```", "").strip()
                        data = json.loads(clean_text)
                        
                        # Veritabanına Ekle
                        add_food_log(
                            data.get("food_name", "Bilinmeyen Yemek"),
                            float(data.get("calories", 0)),
                            float(data.get("protein", 0)),
                            float(data.get("carbs", 0)),
                            float(data.get("fat", 0))
                        )
                        st.success(f"Eklendi: {data.get('food_name')} - {data.get('calories')} kcal")
                    except Exception as e:
                        st.error(f"Analiz sırasında bir hata oluştu: {e}")

with col2:
    st.subheader("📈 Bugünkü Özet & Hedefler")
    
    today_logs = load_today_logs()
    total_cal = sum(row[1] for row in today_logs)
    total_protein = sum(row[2] for row in today_logs)
    total_carbs = sum(row[3] for row in today_logs)
    total_fat = sum(row[4] for row in today_logs)
    
    st.metric(label="Günlük Kalori Hedefi", value=f"{int(target_calories)} kcal")
    st.metric(label="Alınan Kalori", value=f"{int(total_cal)} kcal", delta=f"{int(total_cal - target_calories)} kcal")
    
    progress = min(total_cal / target_calories, 1.0) if target_calories > 0 else 0
    st.progress(progress)
    
    st.write(f"**Makro Dağılımı:** 🥩 Protein: {int(total_protein)}g | 🍞 Karbonhidrat: {int(total_carbs)}g | 🥑 Yağ: {int(total_fat)}g")
    
    st.divider()
    st.subheader("📝 Bugünkü Yemekler")
    if today_logs:
        for item in today_logs:
            st.write(f"• **{item[0]}**: {int(item[1])} kcal (P: {int(item[2])}g, K: {int(item[3])}g, Y: {int(item[4])}g)")
        if st.button("Bugünkü Geçmişi Temizle"):
            clear_today_logs()
            st.rerun()
    else:
        st.write("Henüz bir yemek eklenmedi.")
