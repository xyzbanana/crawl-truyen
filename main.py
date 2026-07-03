from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from curl_cffi import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

@app.get("/api/crawl-info")
def crawl_comic_info(url: str = Query(...)):
    try:
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}/"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": base_url,
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        session = requests.Session()

        # Vào trang chủ trước để lấy cookie
        session.get(
            base_url,
            headers=headers,
            impersonate="chrome120",
            timeout=15
        )

        time.sleep(1)

        response = session.get(
            url,
            headers=headers,
            impersonate="chrome120",
            timeout=15
        )

        if response.status_code == 403:
            raise HTTPException(
                status_code=403,
                detail="Web gốc chặn IP/server crawl. Render thường bị chặn do IP datacenter."
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Web gốc không phản hồi đúng. Code: {response.status_code}"
            )

        soup = BeautifulSoup(response.text, "html.parser")
        book_info = soup.find("div", class_="book_info")

        if not book_info:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy div.book_info. Có thể web đã đổi HTML hoặc trả trang chống bot."
            )

        img_tag = book_info.select_one("div.book_avatar img")
        cover_url = ""
        if img_tag:
            cover_url = img_tag.get("src") or img_tag.get("data-src") or img_tag.get("data-fb") or ""

        title_tag = book_info.find("h1", itemprop="name")
        title = title_tag.get_text(strip=True) if title_tag else ""

        other_name = author = translation_team = total_chapters = status = ""

        list_info = book_info.find("ul", class_="list-info")
        if list_info:
            for li in list_info.find_all("li", class_="row"):
                classes = li.get("class", [])
                value_p = li.find("p", class_="col-xs-9") or li.find("p", class_="other-name")
                value_text = value_p.get_text(strip=True) if value_p else ""

                if "othername" in classes:
                    other_name = value_text
                elif "author" in classes:
                    author = value_text
                elif "team" in classes:
                    translation_team = value_text
                else:
                    name_p = li.find("p", class_="name")
                    if name_p:
                        name_text = name_p.get_text(strip=True).lower()
                        if "tổng số chap" in name_text:
                            total_chapters = value_text
                        elif "tình trạng" in name_text:
                            status = value_text

        genres = []
        list_genres = book_info.find("ul", class_="list01")
        if list_genres:
            genres = [
                genre.get_text(strip=True)
                for genre in list_genres.find_all("li", class_="li03")
                if genre.get_text(strip=True)
            ]

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

    except HTTPException:
        raise

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Lỗi hệ thống khi crawl",
                "error_type": type(e).__name__,
                "error_details": str(e)
            }
        )
