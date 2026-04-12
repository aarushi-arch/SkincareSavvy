"""Find Purplle's real API by checking network calls embedded in the page."""
import requests, re, json

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}

# 1. Check the __INITIAL_STATE__ or __NEXT_DATA__ embedded JSON
r = requests.get('https://www.purplle.com/skin/moisturizers', headers=headers, timeout=15)
print('Page status:', r.status_code, '| Size:', len(r.text))

# Look for embedded JSON state
for pattern in [r'__INITIAL_STATE__\s*=\s*({.{20,500}})', r'__NEXT_DATA__\s*=\s*({.{20,500}})']:
    m = re.search(pattern, r.text)
    if m:
        print('Found embedded state:', m.group(1)[:200])

# 2. Try Purplle's known listing endpoint format
test_urls = [
    'https://www.purplle.com/api/v2/products/listing?category_id=8&page=1&per_page=20',
    'https://www.purplle.com/api/v2/categories/8/products?page=1',
    'https://www.purplle.com/api/v2/search?q=moisturizer&page=1',
    'https://www.purplle.com/api/v1/search/products?q=moisturizer',
    'https://www.purplle.com/api/v2/products?category=moisturizers&page=1&per_page=20',
    'https://www.purplle.com/api/v2/products/category/moisturizers?page=1',
]

api_headers = {**headers, 'Accept': 'application/json, text/plain, */*', 'Referer': 'https://www.purplle.com/'}
for url in test_urls:
    try:
        resp = requests.get(url, headers=api_headers, timeout=10)
        ct = resp.headers.get('content-type', '')
        print(f'{resp.status_code} | {ct[:30]} | {url.split("purplle.com")[1][:60]}')
        if resp.status_code == 200 and 'json' in ct:
            print('  JSON preview:', resp.text[:200])
    except Exception as e:
        print(f'ERROR | {url[:60]} | {e}')
