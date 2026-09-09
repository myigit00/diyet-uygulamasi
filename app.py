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
    # Yemek geçmişi tablosu (meal_type eklendi)
    c.execute('''
        CREATE TABLE IF NOT EXISTS food_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            meal_type TEXT,
            food_name TEXT,
            calories REAL,
            protein REAL,
            carbs REAL,
            fat REAL
        )
    ''')
    # Su takibi tablosu
    c.execute('''
        CREATE TABLE IF NOT EXISTS water_logs (
            date TEXT PRIMARY KEY,
            amount_ml INTEGER
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

def add_food_log(meal_type, food_name, calories, protein, carbs, fat):
    today = str(datetime.date.today())
    conn = sqlite3.connect("diyet_takip.db")
    c = conn.cursor()
    c.execute('''
        INSERT INTO food_logs (date, meal_type, food_name, calories, protein, carbs, fat)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (today, meal_type, food_name, calories, protein, carbs, fat))
    conn.commit()
    conn.close()

def delete_food_log(log_id):
    conn = sqlite3.connect("diyet_takip.db")
    c = conn.cursor()
    c.execute("DELETE FROM food_logs WHERE id = ?", (log_id,))
    conn.commit()
    conn.close()

def load_today_logs():
    today = str(datetime.date.today())
    conn = sqlite3.connect("diyet_takip.db")
    c = conn.cursor()
    c.execute("SELECT id, meal_type, food_name, calories, protein, carbs, fat FROM food_logs WHERE date = ?", (today,))
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

# Su Takibi Fonksiyonları
def get_today_water():
    today = str(datetime.date.today())
    conn = sqlite3.connect("diyet_takip.db")
    c = conn.cursor()
    c.execute("SELECT amount_ml FROM water_logs WHERE date = ?", (today,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

def add_water(amount=250):
    today = str(datetime.date.today())
    current = get_today_water()
    new_total = current + amount
    conn = sqlite3.connect("diyet_takip.db")
    c = conn.cursor()
    c.execute('''
        INSERT INTO water_logs (date, amount_ml) VALUES (?, ?)
        ON CONFLICT(date) DO UPDATE SET amount_ml = excluded.amount_ml
    ''', (today, new_total))
    conn.commit()
    conn.close()

def reset_water():
    today = str(datetime.date.today())
    conn = sqlite3.connect("diyet_takip.db")
    c = conn.cursor()
    c.execute("DELETE FROM water_logs WHERE date = ?", (today,))
    conn.commit()
    conn.close()

# Veritabanını Başlat
init_db()

# --- STREAMLIT ARAYÜZÜ ---
st.set_page_config(page_title="AI Diyet & Beslenme Takibi", page_icon="🥗", layout="wide")
st.title("🥗 Yapay Zeka Destekli Kalori ve Makro Takibi")

# API Key Kontrolü
api_key = st.secrets.get("GEMINI_API_KEY", "")
if not api_key:
    api_key = st.sidebar.text_input("Gemini API Key Giriniz", type="password")

# Profil Yükle
saved_profile = load_profile()

# --- YAN MENÜ: PROFİL ---
st.sidebar.header("📊 Profil ve Metrikler")

default_age = saved_profile["age"] if saved_profile else 17
default_gender = saved_profile["gender"] if saved_profile else "Erkek"
default_height = saved_profile["height"] if saved_profile else 173.8
default_weight = saved_profile["weight"] if saved_profile else 84.5
default_activity = saved_profile["activity"] if saved_profile else "Orta Hareketli"
default_goal = saved_profile["goal"] if saved_profile else "Kilo Ver"

gender = st.sidebar.radio("Cinsiyet", ["Erkek", "Kadın"], index=0 if default_gender == "Erkek" else 1)
age = st.sidebar.number_input("Yaş", min_value=10, max_value=100, value=default_age)
height = st.sidebar.number_input("Boy (cm)", min_value=100.0, max_value=250.0, value=default_height)
weight = st.sidebar.number_input("Kilo (kg)", min_value=30.0, max_value=250.0, value=default_weight)

activity_options = ["Hareketsiz", "Az Hareketli", "Orta Hareketli", "Çok Hareketli"]
activity_idx = activity_options.index(default_activity) if default_activity in activity_options else 2
activity = st.sidebar.selectbox("Aktivite Seviyesi", activity_options, index=activity_idx)

goal_options = ["Kilo Ver", "Kilo Koru", "Kilo Al"]
goal_idx = goal_options.index(default_goal) if default_goal in goal_options else 0
goal = st.sidebar.selectbox("Hedef", goal_options, index=goal_idx)

if st.sidebar.button("Profil Bilgilerini Kaydet"):
    save_profile(age, gender, height, weight, activity, goal)
    st.sidebar.success("Profil kaydedildi!")

# --- HESAPLAMALAR ---
if gender == "Erkek":
    bmr = 10 * weight + 6.25 * height - 5 * age + 5
else:
    bmr = 10 * weight + 6.25 * height - 5 * age - 161

activity_multipliers = {"Hareketsiz": 1.2, "Az Hareketli": 1.375, "Orta Hareketli": 1.55, "Çok Hareketli": 1.725}
tdee = bmr * activity_multipliers.get(activity, 1.55)

if goal == "Kilo Ver":
    target_calories = tdee - 500
elif goal == "Kilo Al":
    target_calories = tdee + 500
else:
    target_calories = tdee

# Makro Hedefleri (%30 Protein, %45 Karbonhidrat, %25 Yağ)
target_protein = (target_calories * 0.30) / 4
target_carbs = (target_calories * 0.45) / 4
target_fat = (target_calories * 0.25) / 9

# --- ANA EKRAN DÜZENİ ---
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📸 Öğün Yükle & Analiz Et")
    meal_type = st.selectbox("Öğün Tipi", ["Kahvaltı", "Öğle Yemeği", "Akşam Yemeği", "Atıştırmalık"])
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
                        
                        add_food_log(
                            meal_type,
                            data.get("food_name", "Bilinmeyen Yemek"),
                            float(data.get("calories", 0)),
                            float(data.get("protein", 0)),
                            float(data.get("carbs", 0)),
                            float(data.get("fat", 0))
                        )
                        st.success(f"Eklendi: {data.get('food_name')} ({data.get('calories')} kcal)")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Analiz sırasında bir hata oluştu: {e}")

    st.divider()
    # --- SU TAKİBİ BÖLÜMÜ ---
    st.subheader("💧 Günlük Su Takibi")
    today_water = get_today_water()
    water_target = 3000 # 3 Litre hedef
    
    w_col1, w_col2, w_col3 = st.columns([2, 1, 1])
    with w_col1:
        st.write(f"Tüketilen: **{today_water} ml** / {water_target} ml")
        st.progress(min(today_water / water_target, 1.0))
    with w_col2:
        if st.button("+250 ml Su"):
            add_water(250)
            st.rerun()
    with w_col3:
        if st.button("Sıfırla"):
            reset_water()
            st.rerun()

with col2:
    st.subheader("📈 Bugünkü Özet & Hedefler")
    
    today_logs = load_today_logs()
    total_cal = sum(row[3] for row in today_logs)
    total_protein = sum(row[4] for row in today_logs)
    total_carbs = sum(row[5] for row in today_logs)
    total_fat = sum(row[6] for row in today_logs)
    
    # Kalori Özeti
    c1, c2 = st.columns(2)
    with c1:
        st.metric(label="Günlük Kalori Hedefi", value=f"{int(target_calories)} kcal")
    with c2:
        st.metric(label="Alınan Kalori", value=f"{int(total_cal)} kcal", delta=f"{int(total_cal - target_calories)} kcal")
    
    st.caption("Kalori İlerlemesi")
    st.progress(min(total_cal / target_calories, 1.0) if target_calories > 0 else 0)
    
    st.divider()
    
    # Detaylı Makro Hedefleri & İlerleme Çubukları
    st.write("### 🥩 Makro İlerlemesi & Hedefler")
    
    # Protein
    st.write(f"**Protein:** {int(total_protein)}g / {int(target_protein)}g")
    st.progress(min(total_protein / target_protein, 1.0) if target_protein > 0 else 0)
    
    # Karbonhidrat
    st.write(f"**Karbonhidrat:** {int(total_carbs)}g / {int(target_carbs)}g")
    st.progress(min(total_carbs / target_carbs, 1.0) if target_carbs > 0 else 0)
    
    # Yağ
    st.write(f"**Yağ:** {int(total_fat)}g / {int(target_fat)}g")
    st.progress(min(total_fat / target_fat, 1.0) if target_fat > 0 else 0)
    
    st.divider()
    st.subheader("📝 Bugünkü Yemekler")
    if today_logs:
        for item in today_logs:
            # item: (id, meal_type, food_name, calories, protein, carbs, fat)
            log_id, m_type, name, cal, p, c, f = item
            f_col1, f_col2 = st.columns([4, 1])
            with f_col1:
                st.write(f"• **[{m_type}] {name}**: {int(cal)} kcal (P:{int(p)}g, K:{int(c)}g, Y:{int(f)}g)")
            with f_col2:
                if st.button("🗑️ Sil", key=f"del_{log_id}"):
                    delete_food_log(log_id)
                    st.rerun()
        
        st.write("---")
        if st.button("Tüm Günü Temizle"):
            clear_today_logs()
            st.rerun()
    else:
        st.write("Henüz bir yemek eklenmedi.")
