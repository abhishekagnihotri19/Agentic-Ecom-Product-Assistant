import os
import csv
import time
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from prod_assistant.utils.model_loader import safe_text


import re

class FlipkartScrapper:
    def __init__(self, output_dir="data"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok= True)

    def get_top_reviews (self, product_url, count = 2):
        """Get Top reviews of Products"""
        options= uc.ChromeOptions()
        options.add_argument ("--no-sandbox")
        options.add_argument("--disable-blink-feature = Automation-Controlled")
        driver=uc.Chrome(options =options,  version_main=144, use_subprocess= True)

        if not product_url.startswith("http"):
            driver.quit()
            return "No Review found"
        
        try:
            driver.get(product_url)
            driver.sleep(4)

            try:

                driver.find_element (By.XPATH,"//button[contains((text(), 'X')]").click()
                time.sleep(1)
            except Exception as e:
                print (f"Error occuring while closing popup: {e}")

            for _ in range(4):
                ActionChains(driver).send_keys(Keys.END).perform()

            html= driver.page_source

            soup = BeautifulSoup(html, "html.parser")
            review_block= soup.select("div._27M-vq, div.col.EPCmJX, div._6K-7Co, div.lvJbLV.col-12-12")
            seen =set()
            reviews= []
            for block in review_block:
                text= block.get_text(separator= " ", strip= True)
                if text and text not in seen:
                    reviews.append(text)
                    seen.add(text)
                if len(reviews) > count:
                    break
        except Exception:
            reviews= [] # Either:✔ All steps succeed → commit reviews or ❌ Any step fails → rollback to empty
        driver.quit()
        return "||". join(reviews) if reviews else "No Review found"
    
    def scrap_flipkart_product(self, query, max_products=2, review_count=2):

        options = uc.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-blink-features=AutomationControlled")

        driver = uc.Chrome(
            options=options,
            version_main=144,
            use_subprocess=True
        )

        search_url = f"https://www.flipkart.com/search?q={query.replace(' ', '+')}"
        driver.get(search_url)
        time.sleep(4)

        # Popup (optional)
        try:
            driver.find_element(
                By.XPATH,
                "//button[contains(text(),'✕') or contains(text(),'X')]"
            ).click()
            time.sleep(1)
        except Exception:
            pass

        products = []

        items = driver.find_elements(By.CSS_SELECTOR, "div[data-id]")[:max_products]

        for item in items:
            try:
                #title = safe_text(item, By.CSS_SELECTOR, "a[title]")
                #price = safe_text(item, By.CSS_SELECTOR, "div[class*='price']")
                #rating = safe_text(item, By.CSS_SELECTOR, "div[class*='rating'], span[class*='rating']")
                raw_text = item.text

                # Title → first line
                title = raw_text.split("\n")[0]

                # Price
                price_match = re.search(r"₹\s?[\d,]+", raw_text)
                price = price_match.group(0) if price_match else "N/A"

                # Rating
                rating_match = re.search(r"\b\d(\.\d)?\b", raw_text)
                rating = rating_match.group(0) if rating_match else "N/A"


                reviews_text = item.text
                match = re.search(r"\d+(,\d+)?(?=\s+Reviews)", reviews_text)
                total_review = match.group(0) if match else "N/A"

                link_el = item.find_element(By.CSS_SELECTOR, "a[href*='/p/']")
                href = link_el.get_attribute("href")
                product_link = href if href.startswith("http") else "https://www.flipkart.com" + href

                match = re.findall(r"/p/(itm[0-9A-Za-z]+)", product_link)
                product_id = match[0] if match else "N/A"

            except Exception as e:
                print(f"Skipping item due to error: {e}")
                continue

            top_reviews = (
                self.get_top_reviews(product_link, count=review_count)
                if "flipkart.com" in product_link else "Invalid product URL"
            )

            products.append([
                product_id,
                title,
                price,
                rating,
                total_review,
                top_reviews
            ])

        driver.quit()
        return products

    
    
    def save_to_csv (self, data, file_name = "product_reviews.csv"):
        """"Save the Scrapped product review into CSV"""
        if os.path.isabs(file_name):
            path= file_name
        elif os.path.dirname(file_name):
            path= file_name
            os.makedirs(os.path.dirname(path),exist_ok=True)
        else:
            path= os.path.join(self.output_dir, file_name)

        with open(path, "w", newline="", encoding= "utf-8" ) as f:
            writer= csv.writer(f)
            writer.writerow(["product_id", "title", "price", "rating", "total_review", "top_reviews"])
            writer.writerows(data)







        

