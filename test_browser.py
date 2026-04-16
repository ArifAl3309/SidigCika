from playwright.sync_api import sync_playwright

def test():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        
        errors = []
        page.on("pageerror", lambda err: errors.append(err))
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        
        page.goto("http://localhost:8000/guru.html")
        page.wait_for_timeout(2000)
        
        print(f"ERRORS: {errors}")
        
        # also print html of leaderbord
        print(page.locator("#leaderboard-body").inner_html())
        browser.close()

if __name__ == "__main__":
    test()
