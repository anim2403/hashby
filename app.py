import streamlit as st
import requests
from bs4 import BeautifulSoup


st.title("Web Content Scraper")
st.write("Enter a URL to scrape its content")


url = st.text_input("Enter URL:", "https://example.com")

if 'scraped_content' not in st.session_state:
    st.session_state.scraped_content = ""

def scrape_url(url):
    try:
       
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()  
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        
        for script_or_style in soup(['script', 'style']):
            script_or_style.decompose()
            
       
        text = soup.get_text()
        
        
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text
    except Exception as e:
        return f"Error: {str(e)}"


if st.button("Scrape Content"):
    with st.spinner("Scraping content..."):
        st.session_state.scraped_content = scrape_url(url)
    st.success("Content scraped successfully!")


if st.session_state.scraped_content:
    st.subheader("Scraped Content")
    st.text_area("Content", st.session_state.scraped_content, height=400)

