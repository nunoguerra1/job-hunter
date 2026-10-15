import json

import httpx

r = httpx.get(
    "https://portal.gupy.io/api/job-search/jobs",
    params={"jobName": "estagio desenvolvimento", "limit": 3, "offset": 0},
    timeout=30,
)
data = r.json()["data"]
print("total de itens:", len(data))
for item in data[:2]:
    item = {k: v for k, v in item.items() if k != "description"}
    print(json.dumps(item, indent=2, ensure_ascii=False))
    print("-" * 40)