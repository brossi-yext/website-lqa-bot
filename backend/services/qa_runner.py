# backend/services/qa_runner.py
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

# -----------------------
# Helper functions
# -----------------------
def extract_text_nodes(html: str):
    """Return a list of all visible text nodes, stripped and filtered."""
    soup = BeautifulSoup(html, "html.parser")
    texts = []
    for element in soup.find_all(text=True):
        if element.parent.name in ["script", "style", "noscript"]:
            continue
        text = element.strip()
        if text:
            texts.append(text)
    return texts

def extract_links(html: str):
    """Return list of href links in the page."""
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        links.append(a["href"])
    return links

def extract_structure_with_text(html: str):
    """
    Extract structure identifiers and text for sections/modules.
    Returns a list of tuples: (identifier, text_snippet)
    """
    soup = BeautifulSoup(html, "html.parser")
    sections = []
    for tag in soup.find_all(["h1","h2","h3","section","article","div"]):
        identifier = tag.name
        if tag.get("id"):
            identifier += f"#{tag['id']}"
        elif tag.get("class"):
            identifier += f".{'.'.join(tag['class'])}"

        # get text content inside the tag
        text = tag.get_text(separator=" ", strip=True)
        # optionally truncate to first 100 chars
        if len(text) > 100:
            text = text[:100] + "…"

        sections.append((identifier, text))
    return sections

# -----------------------
# Main QA function
# -----------------------
def run_qa_multilingual(url_path: str, languages: list[str]):
    """
    Run QA on English page and compare with localized versions.
    Returns dictionary of findings per language.
    """
    results = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--disable-popup-blocking"])
        page = browser.new_page()

        # --------------------
        # 1️⃣ English baseline
        # --------------------
        english_url = f"https://www.yext.com/{url_path}"
        try:
            page.goto(english_url, wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            print(f"Failed to load English page {english_url}: {e}")
            return {"en": {"url": english_url, "error": str(e)}}

        english_title = page.title()
        english_html = page.content()
        english_text_nodes = extract_text_nodes(english_html)
        english_sections = extract_structure_with_text(english_html)
        english_links = extract_links(english_html)

        results["en"] = {
            "url": english_url,
            "title": english_title,
            "text_nodes_count": len(english_text_nodes),
            "sections_count": len(english_sections),
            "links_count": len(english_links)
        }

        # --------------------
        # 2️⃣ Localized pages
        # --------------------
        for locale in languages:
            localized_url = f"https://www.yext.com/{locale}/{url_path}"
            try:
                page.goto(localized_url, wait_until="domcontentloaded", timeout=30000)
            except Exception as e:
                print(f"Failed to load {localized_url}: {e}")
                results[locale] = {"url": localized_url, "error": str(e)}
                continue

            title = page.title()
            html = page.content()
            text_nodes = extract_text_nodes(html)
            sections = extract_structure_with_text(html)
            links = extract_links(html)

            # --------------------
            # Compare structure and capture missing sections with text
            # --------------------
            missing_in_translation = []
            english_identifiers = {identifier: text for identifier, text in english_sections}
            translated_identifiers = {identifier for identifier, _ in sections}

            for identifier, text in english_sections:
                if identifier not in translated_identifiers:
                    missing_in_translation.append({"section": identifier, "text": text})

            extra_in_translation = []
            for identifier, text in sections:
                if identifier not in english_identifiers:
                    extra_in_translation.append({"section": identifier, "text": text})

            # --------------------
            # Flag untranslated text (exact match)
            # --------------------
            untranslated_text = [t for t in text_nodes if t in english_text_nodes]

            # --------------------
            # Check links (slow if many)
            # --------------------
            broken_links = []
            for link in links:
                try:
                    resp = page.goto(link, wait_until="domcontentloaded", timeout=5000)
                    if resp is None or resp.status >= 400:
                        broken_links.append(link)
                except:
                    broken_links.append(link)

            # --------------------
            # Store results
            # --------------------
            results[locale] = {
                "url": localized_url,
                "title": title,
                "text_nodes_count": len(text_nodes),
                "sections_count": len(sections),
                "missing_sections": missing_in_translation,
                "extra_sections": extra_in_translation,
                "untranslated_text": untranslated_text,
                "links_count": len(links),
                "broken_links": broken_links
            }

        browser.close()
    return results
