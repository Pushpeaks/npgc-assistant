import httpx
from bs4 import BeautifulSoup
import json
import os
import asyncio

URLS = {
    "admission_schedule": "https://www.npgc.in/Admission-AdmissionSchedules.aspx",
    "ug_courses": "https://www.npgc.in/Academics-CoursesUG.aspx",
    "pg_courses": "https://www.npgc.in/Academics-CoursesPG.aspx",
    "contact": "https://www.npgc.in/ContactUs.aspx",
    "departments": "https://www.npgc.in/Academics-Department.aspx"
}

async def scrape_page(url):
    print(f"Scraping: {url}")
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url)
            if response.status_code == 200:
                return response.text
            else:
                print(f"Failed to fetch {url}: {response.status_code}")
                return None
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None

def parse_table(soup):
    tables = []
    for table in soup.find_all('table'):
        rows = []
        for tr in table.find_all('tr'):
            cells = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
            if any(cells):
                rows.append(cells)
        if rows:
            tables.append(rows)
    return tables

def parse_text(soup):
    # Focus on main content areas to avoid header/footer noise
    content = soup.find('div', {'id': 'content'}) or soup.find('main') or soup.find('body')
    if content:
        # Remove script and style elements
        for script_or_style in content(['script', 'style']):
            script_or_style.decompose()
        return content.get_text(separator=' ', strip=True)
    return ""

async def main():
    knowledge_base = {}
    
    for key, url in URLS.items():
        html = await scrape_page(url)
        if html:
            soup = BeautifulSoup(html, 'html.parser')
            knowledge_base[key] = {
                "url": url,
                "text": parse_text(soup),
                "tables": parse_table(soup)
            }
        await asyncio.sleep(1) # Be polite

    output_path = os.path.join(os.getcwd(), "scraped_data.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(knowledge_base, f, indent=2, ensure_ascii=False)
    
    print(f"\nScraping complete! Data saved to: {output_path}")

if __name__ == "__main__":
    asyncio.run(main())
