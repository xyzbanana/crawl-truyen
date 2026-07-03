from fastapi import FastAPI, HTTPException, Query
import cloudscraper
from bs4 import BeautifulSoup

app = FastAPI(title="Comic Info Scraper API")

@app.get("/api/crawl-info")
async def crawl_comic_info(url: str = Query(..., description="Link chi tiết của truyện tranh từ TruyenQQ")):
    try:
        # Khởi tạo scraper giả lập trình duyệt vượt Cloudflare
        scraper = cloudscraper.create_scraper()
        
        # Gửi request lấy mã nguồn HTML
        response = scraper.get(url)
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code, 
                detail=f"Không thể kết nối đến website gốc. Mã lỗi: {response.status_code}"
            )
            
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Tìm block tổng chứa thông tin truyện như bạn cung cấp
        book_info = soup.find("div", class_="book_info")
        if not book_info:
            raise HTTPException(status_code=404, detail="Không tìm thấy thẻ div.book_info trên trang này.")
            
        # 1. Lấy link ảnh bìa (Ưu tiên lấy từ src, nếu lỗi lấy từ data-fb)
        img_tag = book_info.find("div", class_="book_avatar").find("img") if book_info.find("div", class_="book_avatar") else None
        cover_url = ""
        if img_tag:
            cover_url = img_tag.get("src") or img_tag.get("data-fb") or ""

        # 2. Lấy tên truyện chính
        title_tag = book_info.find("h1", itemprop="name")
        title = title_tag.text.strip() if title_tag else ""

        # Tạo một bộ khung dữ liệu rỗng để lưu các thông tin trong danh sách <ul class="list-info">
        other_name = ""
        author = ""
        translation_team = ""
        total_chapters = ""
        status = ""

        # Duyệt qua các dòng <li> trong danh sách thông tin truyện
        list_info = book_info.find("ul", class_="list-info")
        if list_info:
            li_tags = list_info.find_all("li", class_="row")
            for li in li_tags:
                # Kiểm tra class của dòng để phân loại dữ liệu
                classes = li.get("class", [])
                
                # Cột text giá trị thường nằm ở thẻ <p class="... col-xs-9">
                value_p = li.find("p", class_="col-xs-9") or li.find("p", class_="other-name")
                value_text = value_p.text.strip() if value_p else ""
                
                if "othername" in classes:
                    other_name = value_text
                elif "author" in classes:
                    author = value_text
                elif "team" in classes:
                    translation_team = value_text
                else:
                    # Trường hợp tổng số chap hoặc tình trạng không có class định danh riêng biệt, ta dựa vào text của tiêu đề <p class="name">
                    name_p = li.find("p", class_="name")
                    if name_p:
                        name_text = name_p.text.lower()
                        if "tổng số chap" in name_text:
                            total_chapters = value_text
                        elif "tình trạng" in name_text:
                            status = value_text

        # 3. Lấy danh sách thể loại truyện từ <ul class="list01">
        genres = []
        list_genres = book_info.find("ul", class_="list01")
        if list_genres:
            genre_tags = list_genres.find_all("li", class_="li03")
            genres = [genre.text.strip() for genre in genre_tags if genre.text]

        # Trả về kết quả JSON dạng sạch, không lưu trữ gì trên server Render
        return {
            "status": "success",
            "data": {
                "title": title,
                "other_name": other_name,
                "cover_url": cover_url,
                "author": author,
                "translation_team": translation_team,
                "total_chapters": total_chapters,
                "status": status,
                "genres": genres
            }
        }
        
    except Exception as e:
			raise HTTPException(status_code=500, detail=f"Lỗi hệ thống khi crawl: {str(e)}")