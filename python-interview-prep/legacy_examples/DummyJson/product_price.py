import requests
from collections import defaultdict
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

response = requests.get(
    "https://dummyjson.com/products",
    verify=False
)

data = response.json()

category_count = defaultdict(int)

for product in data["products"]:
    category_count[product["category"]] += 1

for category, count in category_count.items():
    print(f"{category}: {count}")