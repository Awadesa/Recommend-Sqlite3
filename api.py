from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import requests


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================================
# 1) جلب المنتجات من API PHP
# ======================================

def get_products():
    url = "https://qasimshutta.shop/2test/e-commerce-halfa/products/get_products_without_catogery.php"

    response = requests.post(url)
    if response.status_code == 200:
        try:
            data = response.json()
            return data.get("data", [])
        except ValueError:
            print("JSON غير صالح:", response.text)
            return []
    else:
        print("خطأ في الطلب:", response.status_code)
        return []

# ======================================
# 2) جلب المنتجات المفضلة للمستخدم
# ======================================

def get_favorites(user_id: int):
    url = "https://qasimshutta.shop/2test/e-commerce-halfa/products/get_products_without_catgoery_with_fav.php"
    payload = {"user_id": user_id}

    response = requests.post(url, data=payload)
    if response.status_code == 200:
        try:
            data = response.json()
            fav_list = []

            for product in data.get("data", []):
                if product.get("fav") == 1:
                    fav_list.append(product)

            return fav_list

        except ValueError:
            print("JSON غير صالح:", response.text)
            return []

    else:
        print("خطأ:", response.status_code)
        return []

# ======================================
# 3) دالة حساب تشابه النصوص
# ======================================

def text_similarity(a, b):
    if not a or not b:
        return 0
    s1 = set(a.split())
    s2 = set(b.split())
    common = s1.intersection(s2)
    return len(common) / max(len(s1), len(s2))

# ======================================
# 4) بناء محتوى المستخدم (وصف + فئات)
# ======================================

def build_user_profile(user_id: int):
    favorites = get_favorites(user_id)
    if not favorites:
        return None, None

    # جمع كل النصوص وكل الفئات
    texts = []
    categories = []

    for fav in favorites:
        desc = fav.get("product_desc_ar", "")
        cat = fav.get("catogeries_name_ar", "")

        if desc:
            texts.append(desc)

        if cat:
            categories.append(cat)

    # نص واحد يحتوي كل أوصاف المفضلة
    final_text = " ".join(texts)

    return final_text, categories

# ======================================
# 5) نظام التوصيات
# ======================================

def recommend(user_id: int, top_n: int=5):

    products = get_products()
    user_text, user_categories = build_user_profile(user_id)

    if not user_text:
        raise Exception("لا توجد منتجات مفضلة للمستخدم!")

    results = []

    for p in products:

        # تشابه الفئات
        category_score = 1 if p.get("catogeries_name_ar") in user_categories else 0

        # تشابه الأوصاف
        desc_score = text_similarity(
            p.get("product_desc_ar", ""),
            user_text
        )

        # المعادلة النهائية
        final_similarity = (category_score * 0.6) + (desc_score * 0.4)

        p["similarity"] = final_similarity
        results.append(p)

    # ترتيب النتائج
    results.sort(key=lambda x: x["similarity"], reverse=True)
    return results[:top_n]

# ======================================
# 6) API Endpoint
# ======================================

class RecommendRequest(BaseModel):
    user_id: int
    top_n: int = 5

@app.post("/recommend")
def get_recommendations(data: RecommendRequest):
    try:
        recs = recommend(data.user_id, data.top_n)
        #  عرض كل بيانات المنتجات المقترحة
        # return {"status": "success", "recommendations": recs}
        # عرض ال id الخاص بالمنتجات المقترحة فقط
        return {"status": "success", "recommendations": [r['products_id'] for r in recs]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
