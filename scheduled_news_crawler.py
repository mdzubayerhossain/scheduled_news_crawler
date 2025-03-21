import requests
from bs4 import BeautifulSoup
import csv
import time
import random
import re
import os
from datetime import datetime

def clean_text(text):
    """Clean text by removing extra whitespace and newlines"""
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def get_current_articles():
    """Get list of article URLs already scraped"""
    existing_urls = set()
    
    # Create data directory if it doesn't exist
    os.makedirs('data', exist_ok=True)
    
    # Check if history file exists
    if os.path.exists('data/article_history.txt'):
        with open('data/article_history.txt', 'r', encoding='utf-8') as f:
            for line in f:
                existing_urls.add(line.strip())
    
    return existing_urls

def save_article_url(url):
    """Save article URL to history file"""
    with open('data/article_history.txt', 'a', encoding='utf-8') as f:
        f.write(url + '\n')

def scrape_prothom_alo():
    """Scrape latest news articles from Prothom Alo"""
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting scrape cycle...")
    
    # Get already scraped article URLs
    existing_urls = get_current_articles()
    
    # Headers to mimic a browser
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,bn;q=0.8",
    }
    
    # Base URL and homepage URL
    base_url = "https://www.prothomalo.com"
    home_url = base_url
    
    # Create or append to CSV file
    csv_filename = f'data/prothom_alo_{datetime.now().strftime("%Y%m%d")}.csv'
    file_exists = os.path.exists(csv_filename)
    
    with open(csv_filename, 'a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        
        # Write header only if file is new
        if not file_exists:
            writer.writerow(['title', 'full_content', 'image_url', 'article_url', 'published_at', 'scraped_at'])
        
        try:
            print("Fetching homepage to extract article links...")
            response = requests.get(home_url, headers=headers)
            response.raise_for_status()
            
            # Parse homepage HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find article links on the homepage
            article_links = []
            categories = ['bangladesh', 'world', 'economy', 'sports', 'entertainment', 'opinion', 'lifestyle', 'technology']
            
            # Look for article cards or links in major categories
            for category in categories:
                category_selector = f'a[href*="/{category}/"]'
                category_links = soup.select(category_selector)
                
                for element in category_links:
                    href = element.get('href')
                    if href and '/video/' not in href and '/gallery/' not in href:
                        # Make sure it's a full URL
                        if not href.startswith('http'):
                            href = base_url + href
                        article_links.append(href)
            
            # Filter out already scraped articles
            new_articles = [url for url in set(article_links) if url not in existing_urls]
            
            if not new_articles:
                print("No new articles found in this cycle.")
                return 0
                
            print(f"Found {len(new_articles)} new article links. Processing...")
            
            # Process each article
            articles_scraped = 0
            for i, article_url in enumerate(new_articles):
                try:
                    # Add a random delay to avoid being blocked
                    time.sleep(random.uniform(2, 3))
                    
                    print(f"Fetching article {i+1}/{len(new_articles)}: {article_url}")
                    article_response = requests.get(article_url, headers=headers)
                    article_response.raise_for_status()
                    
                    # Parse article HTML
                    article_soup = BeautifulSoup(article_response.text, 'html.parser')
                    
                    # Extract title
                    title_element = article_soup.select_one('h1')
                    title = clean_text(title_element.text) if title_element else "No title found"
                    
                    # Extract publication date
                    date_element = article_soup.select_one('time')
                    published_at = date_element.get('datetime') if date_element else ""
                    
                    # Extract main image
                    image_element = article_soup.select_one('figure img')
                    image_url = ""
                    if image_element:
                        image_url = image_element.get('src')
                        if not image_url:
                            image_url = image_element.get('data-src', '')
                    
                    # FOCUS: Extract content from story-element-text elements
                    article_content = ""
                    
                    # Find all elements with class 'story-element-text'
                    story_elements = article_soup.select('.story-element-text')
                    
                    if story_elements:
                        for element in story_elements:
                            # Extract text from each story element
                            element_text = element.get_text(strip=True)
                            if element_text:
                                article_content += element_text + "\n\n"
                    
                    # Clean up the content
                    article_content = article_content.strip()
                    
                    if not article_content:
                        print(f"No story-element-text found for article: {article_url}")
                        # Fallback: Try another common content selector
                        fallback_elements = article_soup.select('.storyContent p')
                        if fallback_elements:
                            for p in fallback_elements:
                                article_content += p.get_text(strip=True) + "\n\n"
                            article_content = article_content.strip()
                            print(f"Used fallback method and found {len(article_content)} characters")
                        else:
                            article_content = "Content extraction failed - no story-element-text found"
                    
                    # Current timestamp
                    scraped_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Write to CSV
                    writer.writerow([title, article_content, image_url, article_url, published_at, scraped_at])
                    
                    # Add to history
                    save_article_url(article_url)
                    
                    print(f"Saved article successfully ({len(article_content)} characters)")
                    articles_scraped += 1
                    
                except Exception as e:
                    print(f"Error processing article {article_url}: {e}")
                    
            return articles_scraped
                    
        except Exception as e:
            print(f"Error during scraping: {e}")
            return 0

def main():
    print("Starting Prothom Alo News Crawler")
    print("Press Ctrl+C to stop the program")
    
    # Create data directory
    os.makedirs('data', exist_ok=True)
    
    # Keep track of statistics
    total_articles = 0
    cycles = 0
    
    try:
        while True:
            # Run the scraper
            new_articles = scrape_prothom_alo()
            total_articles += new_articles
            cycles += 1
            
            # Print statistics
            print(f"\nCycle {cycles} completed.")
            print(f"Total articles scraped so far: {total_articles}")
            print(f"Next scrape scheduled at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Wait for 10 minutes
            print("Waiting for 10 minutes before next scrape cycle...")
            for i in range(10):
                time.sleep(60)  # Wait 1 minute
                minutes_left = 9 - i
                if minutes_left > 0:
                    print(f"{minutes_left} minutes remaining until next scrape...")
    
    except KeyboardInterrupt:
        print("\nProgram stopped by user.")
        print(f"Total articles scraped: {total_articles}")
        print(f"Total scrape cycles completed: {cycles}")
        print("Exiting...")

if __name__ == "__main__":
    main()
