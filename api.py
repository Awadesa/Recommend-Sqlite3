from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import sqlite3

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def setup_database():
    con = sqlite3.connect("api.db")
    cr = con.cursor()
    cr.execute(f"""
    CREATE TABLE IF NOT EXISTS products (
            product_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            category TEXT,
            color TEXT,
            style TEXT,
            size_available TEXT,
            price REAL,
            description TEXT
        ); 
    """)
    cr.execute(f"""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            gender TEXT,
            age INTEGER,
            size_top TEXT,
            size_bottom TEXT,
            size_shoes TEXT,
            favorite_colors TEXT,
            preferred_styles TEXT,
            preferred_categories TEXT,
            budget_min INTEGER,
            budget_max INTEGER
        );
    """)
    # Insert Data in database
    # cr.execute(f"""
    #     INSERT INTO products (name, category, color, style, size_available, price, description)
    #     VALUES
    #     ("T-shirt Cotton", "tshirt", "black", "casual", "M,L,XL", 6000, "comfortable cotton tshirt"),
    #     ("Jeans Slim Fit", "pants", "blue", "streetwear", "30,32,34", 12000, "slim fit blue jeans"),
    #     ("Formal Shirt", "shirt", "white", "formal", "L,XL", 8000, "white office shirt"),
    #     ("Hoodie Classic", "hoodie", "black", "casual", "L,XL", 15000, "black warm hoodie");
    # """)
    # cr.execute(f"""
    #         INSERT INTO users (name, gender, age, size_top, size_bottom, size_shoes,
    #         favorite_colors, preferred_styles, preferred_categories, budget_min, budget_max)
    #         VALUES
    #         ("Sara", "female", 22, "M", "28", "38",
    #         "white,pink,beige", "casual,classic", "dress,tshirt,skirt", 5000, 20000),
    #
    #         ("Yasir", "male", 30, "L", "34", "43",
    #         "black,gray,olive", "streetwear,sport", "hoodie,pants,tshirt", 8000, 25000),
    #
    #         ("Omar", "male", 27, "M", "32", "42",
    #         "blue,navy,white", "casual,formal", "shirt,pants,shoes", 6000, 30000),
    #
    #         ("Maha", "female", 35, "L", "30", "39",
    #         "black,red,white", "formal,classic", "dress,blazer,shoes", 10000, 35000),
    #
    #         ("Lina", "female", 19, "S", "26", "37",
    #         "pink,purple,white", "trendy,streetwear", "tshirt,hoodie,skirt", 3000, 15000),
    #
    #         ("Hussam", "male", 40, "XL", "36", "44",
    #         "gray,black,navy", "formal,classic", "shirt,blazer,trousers", 15000, 50000),
    #
    #         ("Nour", "female", 28, "M", "29", "38",
    #         "green,beige,white", "casual,natural", "tshirt,dress,skirt", 4000, 18000),
    #
    #         ("Khalid", "male", 24, "L", "32", "42",
    #         "black,white,blue", "sport,streetwear", "tshirt,shoes,hoodie", 5000, 20000),
    #
    #         ("Hanin", "female", 31, "M", "28", "39",
    #         "brown,black,white", "classic,formal", "dress,shirt,bag", 8000, 30000),
    #
    #         ("Fadi", "male", 26, "M", "31", "41",
    #         "white,green,gray", "casual,classic", "tshirt,pants,shirt", 4000, 16000);
    #     """)


    con.commit()
    con.close()

# Create Database And Setup It #
setup_database()

# database connection
def get_connection():
    conn = sqlite3.connect("api.db")
    conn.row_factory = sqlite3.Row  # لإرجاع النتائج كـ dict
    return conn

# -----------------------------
# جلب بيانات المستخدم
# -----------------------------

def get_user_profile(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM users WHERE user_id = {user_id}")
    user = cursor.fetchone()
    conn.close()
    if not user:
        raise Exception(f"User {user_id} not found")
    return dict(user)

# -----------------------------
# جلب المنتجات + الفئة
# -----------------------------

def get_products():
    conn = get_connection()
    cursor = conn.cursor()
    query = f"""
            SELECT name, category, color, style, description From products
        """
    cursor.execute(query)
    products = cursor.fetchall()
    conn.close()
    return [dict(p) for p in products]

# -----------------------------
# خوارزمية تشابه نصوص بسيطة
# -----------------------------
def text_similarity(a, b):
    if not a or not b:
        return 0
    s1 = set(a.split())
    s2 = set(b.split())
    common = s1.intersection(s2)
    return len(common) / max(len(s1), len(s2))

# -----------------------------
# بناء محتوى المستخدم
# -----------------------------
def build_user_content(user):
    return " ".join([
        str(user.get("favorite_colors", "")),
        str(user.get("preferred_styles", "")),
        str(user.get("preferred_categories", "")),
    ])

# -----------------------------
# دالة التوصيات
# -----------------------------
def recommend(user_id: int, top_n: int = 5):
    user = get_user_profile(user_id)
    products = get_products()

    user_text = build_user_content(user)
    user_categories = str(user.get("preferred_categories", "")).split(",")

    results = []

    for p in products:
        # تشابه الفئة
        category_score = (
            1 if str(p["category"]) in user_categories else 0
        )

        # تشابه النص
        desc_score = text_similarity(
            p.get("description", ""),
            user_text
        )

        final_similarity = (
            category_score * 0.5 +
            desc_score * 0.3
        )

        p["similarity"] = final_similarity
        results.append(p)

    results.sort(key=lambda x: x["similarity"], reverse=True)
    return results[:top_n]

# -----------------------------
# API Model
# -----------------------------
class RecommendRequest(BaseModel):
    user_id: int
    top_n: int = 3

# -----------------------------
# API Endpoint
# -----------------------------
@app.post("/recommend")
def get_recommendations(data: RecommendRequest):
    try:
        recs = recommend(data.user_id, data.top_n)
        return {
            "status": "success",
            "recommendations": recs
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))