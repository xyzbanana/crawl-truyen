from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import requests
from bs4 import BeautifulSoup
import traceback

app = FastAPI(title="Comic Scraper API")

# Cấu hình CORS để thoải mái gọi từ mọi ứng dụng/frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Thử nghiệm xem server hoạt động hay chưa
@app.get("/")
def read_root():
    return {"status": "active", "message": "API Crawl đã hoạt động ngon lành!"}

# Endpoint tương đương DetailController trong source PHP của bạn
@app.get("/api/crawl-info")
def crawl_comic_info(url: str = Query(..., description="Link truyện cần lấy thông tin")):
    try:
        # Giả lập Header (Tương đương RequestHeaderMiddleware trong PHP)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'vi,en-US;q=0.9,en;q=0.8',
            'Referer': 'https://truyenqqko.com/',
            'Connection': 'keep-alive'
        }
        
        # Gửi request với thời gian chờ tối đa 15 giây
        response = requests.get(url, headers=headers, timeout=15)
        
        # Nếu bị web gốc trả về 403 hoặc 404, xử lý mượt mà thay vì sập 500
        if response.status_code != 200:
            return {
                "status": "fail",
                "message": f"Không thể lấy dữ liệu. Web gốc phản hồi mã lỗi: {response.status_code}"
            }
            
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Tìm thẻ cha chứa thông tin truyện
        book_info = soup.find("div", class_="book_info")
        if not book_info:
            return {
                "status": "fail",
                "message": "Không tìm thấy cấu hình 'book_info'. Giao diện web gốc có thể đã thay đổi hoặc bạn đang bị chặn."
            }
            
        # --- BÓC TÁCH DỮ LIỆU AN TOÀN ---
        img_wrapper = book_info.find("div", class_="book_avatar")
        img_tag = img_wrapper.find("img") if img_wrapper else None
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
        
    except Exception as e:
        # Nếu có lỗi bất ngờ, in chi tiết ra terminal (iSH) hoặc log (Render) thay vì báo "Internal Server Error" chung chung
        print("--- LỖI HỆ THỐNG CRASH ---")
        traceback.print_exc()
        return {
            "status": "internal_error",
            "error_type": type(e).__name__,
            "message": str(e)
        }
