from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from curl_cffi import requests
from bs4 import BeautifulSoup
import time

app = FastAPI(title="Comic Info Scraper API")

# Thêm cấu hình CORS để tránh bị chặn khi gọi từ Frontend (React/Vue/Web khác)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Thêm một trang Home đơn giản để kiểm tra xem Server đã "Tỉnh" chưa
@app.get("/")
def home():
    return {"status": "active", "message": "API Crawl Truyện đã thức dậy thành công!"}

@app.get("/api/crawl-info")
def crawl_comic_info(url: str = Query(..., description="Link chi tiết của truyện tranh từ TruyenQQ")):
    try:
        # Đặt timeout = 15 giây, nếu trang web gốc không phản hồi thì ngắt luôn, không để Render bị treo Loading
        response = requests.get(url, impersonate="chrome", timeout=15)
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code, 
                detail=f"Web gốc chặn hoặc không phản hồi. Code: {response.status_code}"
            )
            
        soup = BeautifulSoup(response.text, "html.parser")
        book_info = soup.find("div", class_="book_info")
        
        if not book_info:
            raise HTTPException(status_code=404, detail="Không tìm thấy thẻ div.book_info. Có thể cấu hình web đã đổi.")
            
        # --- BẮC TÁCH DỮ LIỆU ---
        img_tag = book_info.find("div", class_="book_avatar").find("img") if book_info.find("div", class_="book_avatar") else None
        cover_url = img_tag.get("src") or img_tag.get("data-fb") or "" if img_tag else ""

        title_tag = book_info.find("h1", itemprop="name")
        title = title_tag.text.strip() if title_tag else ""

        other_name = author = translation_team = total_chapters = status = ""

        list_info = book_info.find("ul", class_="list-info")
        if list_info:
            for li in list_info.find_all("li", class_="row"):
                classes = li.get("class", [])
                value_p = li.find("p", class_="col-xs-9") or li.find("p", class_="other-name")
                value_text = value_p.text.strip() if value_p else ""
                
                if "othername" in classes:
                    other_name = value_text
                elif "author" in classes:
                    author = value_text
                elif "team" in classes:
                    translation_team = value_text
                else:
                    name_p = li.find("p", class_="name")
                    if name_p:
                        name_text = name_p.text.lower()
                        if "tổng số chap" in name_text:
                            total_chapters = value_text
                        elif "tình trạng" in name_text:
                            status = value_text

        genres = []
        list_genres = book_info.find("ul", class_="list01")
        if list_genres:
            genres = [genre.text.strip() for genre in list_genres.find_all("li", class_="li03") if genre.text]

        return {
            "status": "success",
            "data": {
                "title": title, "other_name": other_name, "cover_url": cover_url,
                "author": author, "translation_team": translation_team,
                "total_chapters": total_chapters, "status": status, "genres": genres
            }
        }
        
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Kết nối đến TruyenQQ bị quá hạn (Timeout).")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi: {str(e)}")
