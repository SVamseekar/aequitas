# Google Search Console setup

## Property

1. Open https://search.google.com/search-console  
2. Add property: **URL prefix** `https://aequitas.souravamseekar.com`  
3. Verify ownership (one of):
   - **DNS TXT** on `souravamseekar.com` (recommended), or  
   - **HTML file** upload to Vercel `frontend/public/`, or  
   - **HTML meta tag** in `frontend/index.html` (add verification code from GSC)

## Sitemap

After verification:

1. Sitemaps → Add: `https://aequitas.souravamseekar.com/sitemap.xml`  
2. Confirm status becomes Success after crawl  
3. Request indexing for `/`, `/methodology`, `/about` if needed  

## robots.txt

Already points to the sitemap. Private routes (`/dashboard`, `/auth`, …) are disallowed.

## After Vercel deploy

```bash
curl -sS https://aequitas.souravamseekar.com/sitemap.xml | head -40
curl -sS https://aequitas.souravamseekar.com/robots.txt
```
