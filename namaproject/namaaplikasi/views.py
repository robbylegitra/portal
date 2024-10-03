from django.shortcuts import render, redirect
import json
import requests
from bs4 import BeautifulSoup


# Fungsi untuk memuat konfigurasi portal
def load_portal_config():
    try:
        with open('portal_config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


# Fungsi untuk menyimpan konfigurasi portal
def save_portal_config(config):
    with open('portal_config.json', 'w') as f:
        json.dump(config, f, indent=4)


# Fungsi untuk mendeteksi tag yang mengandung link artikel
def detect_article_link_tags(url):
    try:
        response = requests.get(url)
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.content, 'html.parser')
        tags = {
            "article": None,
            "title": None,
            "link": None
        }

        # Mencari semua tag <a> yang memiliki atribut href
        anchor_tags = soup.find_all('a', href=True)

        for anchor in anchor_tags:
            # Memastikan tag <a> memiliki atribut href
            if 'href' in anchor.attrs:
                # Menentukan tag yang mengandung link
                tags["link"] = 'a'  # Menandakan bahwa kita menggunakan tag <a>

                # Mencari tag judul di sekitar link
                parent = anchor.find_parent()
                if parent:
                    tags["article"] = parent.name if parent.name in ['article', 'div', 'section'] else 'div'
                break  # Hentikan setelah menemukan yang pertama

        return tags if tags["link"] else None  # Kembalikan tag jika ada link

    except Exception as e:
        print(f"Error detecting tags: {e}")
        return None


# Fungsi untuk scraping artikel
def scrape_page(url, article_selector, title_selector, link_selector):
    response = requests.get(url)
    if response.status_code != 200:
        return None

    soup = BeautifulSoup(response.content, 'html.parser')
    articles = []
    seen_links = set()  # Set untuk melacak link yang sudah ada

    for article in soup.select(article_selector):
        title_tag = article.select_one(title_selector)
        if title_tag:
            title = title_tag.get_text(strip=True)
            link = title_tag.select_one(link_selector)['href'] if title_tag.select_one(link_selector) else None
            if link and link not in seen_links:  # Cek duplikat
                articles.append({'title': title, 'link': link})
                seen_links.add(link)  # Tambahkan ke set

    return articles


# Fungsi untuk scraping artikel berdasarkan portal
def scrape_articles(portal_key, total_pages):
    config = load_portal_config()
    portal = config.get(portal_key)

    if not portal:
        return []

    base_url = portal["base_url"]
    article_selector = portal["article_selector"]
    title_selector = portal["title_selector"]
    link_selector = portal["link_selector"]

    articles = []

    for page in range(1, total_pages + 1):
        url = f"{base_url}?page={page}"  # Misalnya, jika portal mendukung pagination dengan parameter `page`
        page_articles = scrape_page(url, article_selector, title_selector, link_selector)
        if page_articles:
            articles.extend(page_articles)

    return articles


def home(request):
    config = load_portal_config()

    if request.method == 'POST':
        if 'add_portal' in request.POST:
            new_base_url = request.POST.get('base_url')
            detected_tags = detect_article_link_tags(new_base_url)

            if detected_tags:
                return render(request, 'index.html', {
                    'detected_tags': detected_tags,
                    'base_url': new_base_url,
                    'portals': config
                })

        elif 'save_portal' in request.POST:
            new_base_url = request.POST.get('base_url')
            article_tag = request.POST.get('article_tag')
            title_tag = request.POST.get('title_tag')
            link_tag = request.POST.get('link_tag')
            portal_key = new_base_url.split('//')[1].split('/')[0]

            config[portal_key] = {
                "base_url": new_base_url,
                "article_selector": article_tag,
                "title_selector": title_tag,
                "link_selector": link_tag
            }
            save_portal_config(config)

        elif 'delete_portal' in request.POST:
            portal_key = request.POST.get('portal_key')
            if portal_key in config:
                del config[portal_key]
                save_portal_config(config)

        else:
            portal_key = request.POST.get('portal')
            total_pages = int(request.POST.get('total_pages', 1))
            data = scrape_articles(portal_key, total_pages)

            return render(request, 'index.html', {'data': data, 'portals': config})

    return render(request, 'index.html', {'portals': config})

# Hapus fungsi edit_portal
