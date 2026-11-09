from playwright.sync_api import sync_playwright
import faulthandler
faulthandler.dump_traceback_later(30,repeat=True)
with sync_playwright() as p:
 print('launch',flush=True)
 browser=p.chromium.launch(channel='msedge',headless=True)
 print('page',flush=True)
 page=browser.new_page();page.goto('about:blank')
 print('close',flush=True);browser.close();print('closed',flush=True)
print('done',flush=True)
