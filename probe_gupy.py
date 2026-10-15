import httpx

HOSTS = [
    "https://portal.gupy.io/api/job-search/jobs",
]
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/json",
}
PARAMS = {"jobName": "estagio", "limit": 2, "offset": 0}

for url in HOSTS:
    for label, headers in (("sem headers", None), ("com User-Agent", HEADERS)):
        try:
            r = httpx.get(url, params=PARAMS, headers=headers, timeout=30, follow_redirects=True)
            print(f"\n== {url} | {label}")
            print("status:", r.status_code)
            print("content-type:", r.headers.get("content-type"))
            print("corpo:", r.text[:400].replace("\n", " "))
        except httpx.HTTPError as error:
            print(f"\n== {url} | {label}\nerro: {error}")