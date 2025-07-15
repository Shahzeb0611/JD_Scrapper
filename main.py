# step1_scrape_reddit_image_resumes.py

import requests
import os
import time
import urllib.parse

HEADERS = {"User-Agent": "Mozilla/5.0"}
RESUME_LINKS_FILE = "resume_links.txt"
SUBREDDIT_URL = "https://www.reddit.com/r/resumes/.json"
MAX_POSTS = 100

def fetch_image_links_from_post(permalink):
    post_url = f"https://www.reddit.com{permalink}.json"
    res = requests.get(post_url, headers=HEADERS)
    if res.status_code != 200:
        return []

    post_json = res.json()
    media_links = []

    try:
        post_data = post_json[0]["data"]["children"][0]["data"]

        # 1. From media_metadata
        if "media_metadata" in post_data:
            for m in post_data["media_metadata"].values():
                if "s" in m and "u" in m["s"]:
                    url = m["s"]["u"].replace("&amp;", "&")
                    media_links.append(url)

        # 2. From gallery_data
        elif "url_overridden_by_dest" in post_data:
            url = post_data["url_overridden_by_dest"]
            if "reddit.com/media?url=" in url:
                # Extract and decode the actual media link
                parsed = urllib.parse.urlparse(url)
                real_url = urllib.parse.parse_qs(parsed.query).get("url", [None])[0]
                if real_url:
                    media_links.append(real_url)
            elif url.endswith((".jpg", ".png", ".webp")):
                media_links.append(url)

    except Exception as e:
        print("Error parsing media:", e)

    return media_links

def scrape_resume_images():
    print("🔍 Scraping r/resumes image posts...")
    after = None
    collected_links = set()
    total_posts = 0

    while total_posts < MAX_POSTS:
        params = {"limit": 25}
        if after:
            params["after"] = after

        res = requests.get(SUBREDDIT_URL, headers=HEADERS, params=params)
        if res.status_code != 200:
            print("Failed to fetch posts:", res.status_code)
            break

        data = res.json()
        posts = data["data"]["children"]
        if not posts:
            break

        for post in posts:
            permalink = post["data"]["permalink"]
            image_links = fetch_image_links_from_post(permalink)
            for link in image_links:
                collected_links.add(link)

        after = data["data"].get("after")
        total_posts += len(posts)

        if not after:
            break

        time.sleep(1)  # Respect Reddit's rate limits

    # Append to the existing file
    with open(RESUME_LINKS_FILE, "a") as f:
        for link in collected_links:
            f.write(link + "\n")

    print(f"✅ Appended {len(collected_links)} new resume image links to {RESUME_LINKS_FILE}")
    
    import os
import requests
import hashlib
from urllib.parse import urlparse

RESUME_LINKS_FILE = "resume_links.txt"
DOWNLOAD_FOLDER = "resumes"

def sanitize_filename(url):
    """
    Create a unique filename from a URL using a hash.
    """
    parsed = urlparse(url)
    name_hash = hashlib.md5(url.encode()).hexdigest()
    ext = os.path.splitext(parsed.path)[-1]
    if not ext or len(ext) > 5:
        ext = ".jpg"  # default to jpg if unknown
    return f"resume_{name_hash}{ext}"

def download_resume_images():
    if not os.path.exists(DOWNLOAD_FOLDER):
        os.makedirs(DOWNLOAD_FOLDER)

    with open(RESUME_LINKS_FILE, "r") as f:
        links = [line.strip() for line in f if line.strip()]

    print(f"🔽 Downloading {len(links)} resume images...")

    for i, url in enumerate(links, 1):
        try:
            filename = sanitize_filename(url)
            filepath = os.path.join(DOWNLOAD_FOLDER, filename)

            if os.path.exists(filepath):
                print(f"✅ Already downloaded: {filename}")
                continue

            print(f"[{i}/{len(links)}] Downloading: {url}")
            res = requests.get(url, stream=True)
            if res.status_code == 200:
                with open(filepath, "wb") as f:
                    for chunk in res.iter_content(1024):
                        f.write(chunk)
                print(f"✅ Saved: {filename}")
            else:
                print(f"❌ Failed: HTTP {res.status_code} - {url}")
        except Exception as e:
            print(f"❌ Error downloading {url}: {e}")


if __name__ == "__main__":
    #scrape_resume_images()

    download_resume_images()