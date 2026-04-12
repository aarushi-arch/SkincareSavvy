import requests, re

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36',
}
r = requests.get('https://www.purplle.com/skin/moisturizers', headers=headers, timeout=15)
api_patterns = re.findall(r'["\'](/api/[^"\']{5,60})["\']', r.text)
unique = list(dict.fromkeys(api_patterns))
print('API patterns found:')
for p in unique[:30]:
    print(' ', p)

# Also look for product slugs / IDs
slugs = re.findall(r'/product/([a-z0-9\-]+)', r.text)
print('\nProduct slugs found:', len(slugs))
for s in slugs[:10]:
    print(' ', s)
