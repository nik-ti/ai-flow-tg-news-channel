
import requests
import json

AI_PARSER_URL = "https://parser.simple-flow.co/parse"

def test_url(url, page_type="detail"):
    print(f"Testing {url} ({page_type})...")
    try:
        resp = requests.post(
            AI_PARSER_URL,
            json={"url": url, "page_type": page_type},
            timeout=30,
        )
        print(f"Status: {resp.status_code}")
        try:
            data = resp.json()
            print(json.dumps(data, indent=2)[:500] + "...")
        except:
            print("Response not JSON:", resp.text[:500])
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Test 1: Detail page (TechCrunch)
    test_url("https://techcrunch.com/2026/02/18/amazon-halts-blue-jay-robotics-project-after-less-than-six-months/")
    
    # Test 2: List page (AiBase)
    test_url("https://news.aibase.com/news", "list")
