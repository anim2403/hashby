import streamlit as st
import requests
from bs4 import BeautifulSoup
import json
import google.generativeai as genai

st.title("Web Content Scraper & Structured Extractor")
st.write("Enter a URL to scrape its content and extract structured data using Gemini")

# Gemini API setup
gemini_api_key = st.sidebar.text_input("Enter Google Gemini API Key:", type="password")
if gemini_api_key:
    genai.configure(api_key=gemini_api_key)

url = st.text_input("Enter URL:", "https://example.com")

if 'scraped_content' not in st.session_state:
    st.session_state.scraped_content = ""
if 'structured_data' not in st.session_state:
    st.session_state.structured_data = {}

def scrape_url(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()  
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove scripts and styles
        for script_or_style in soup(['script', 'style']):
            script_or_style.decompose()
            
        # Get text content
        text = soup.get_text()
        
        # Clean up text
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        page_title = soup.title.string if soup.title else "No title found"
        
        return text, page_title
    except Exception as e:
        return f"Error: {str(e)}", "Error"

def extract_structured_data_with_gemini(text, page_title):
    if not gemini_api_key:
        return {"error": "Please enter your Google Gemini API key in the sidebar"}
    
    # Truncate text if it's too long (Gemini has context limits)
    max_length = 30000  # Gemini Pro has a good context window
    truncated_text = text[:max_length] if len(text) > max_length else text
    
    # Create a prompt for Gemini
    prompt = f"""
    Extract structured information from the following webpage content.
    
    PAGE TITLE: {page_title}
    PAGE CONTENT: 
    {truncated_text}
    
    From the following partial credit card information, extract a structured JSON list.
        Each card should have:
        - card_name
        - issuing_bank
        - joining_fee
        - annual_fee
        - reward_structure
        - cashback_offers
        - other_attributes (optional)

        Focus only on relevant card details. Ignore unrelated text..
    """
    
    try:
        # Initialize Gemini model
        model = genai.GenerativeModel('models/gemini-1.5-pro')
        
        # Generate response
        response = model.generate_content(prompt)
        
        result = response.text
        
        # Try to parse the result as JSON
        try:
            # Clean the result to ensure it's valid JSON
            # Remove markdown code blocks if present
            result = result.replace("```json", "").replace("```", "").strip()
            structured_data = json.loads(result)
            return structured_data
        except json.JSONDecodeError:
            # If not valid JSON, try to extract JSON portion using regex
            import re
            json_match = re.search(r'({[\s\S]*})', result)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except:
                    return {"error": "Could not parse Gemini response as JSON", "raw_response": result}
            else:
                return {"error": "Invalid JSON response from Gemini", "raw_response": result}
                
    except Exception as e:
        return {"error": str(e)}

# Create tabs for different views
tab1, tab2 = st.tabs(["Scraper", "Structured Data"])

with tab1:
    if st.button("Scrape Content"):
        with st.spinner("Scraping content..."):
            st.session_state.scraped_content, page_title = scrape_url(url)
            
            if not st.session_state.scraped_content.startswith("Error"):
                st.success("Content scraped successfully!")
                
                # Process with Gemini if API key is provided
                if gemini_api_key:
                    with st.spinner("Extracting structured data with Gemini..."):
                        st.session_state.structured_data = extract_structured_data_with_gemini(
                            st.session_state.scraped_content, 
                            page_title
                        )
                    st.success("Structured extraction complete!")
                else:
                    st.warning("Enter Google Gemini API key in sidebar to extract structured data")
            else:
                st.error(st.session_state.scraped_content)

    if st.session_state.scraped_content and not st.session_state.scraped_content.startswith("Error"):
        st.subheader("Scraped Content")
        st.text_area("Content", st.session_state.scraped_content, height=300)

with tab2:
    if st.session_state.structured_data:
        st.subheader("Structured Data Extracted by Gemini")
        
        if "error" in st.session_state.structured_data:
            st.error(f"Error: {st.session_state.structured_data['error']}")
            if "raw_response" in st.session_state.structured_data:
                st.text_area("Raw Gemini Response", st.session_state.structured_data["raw_response"], height=200)
        else:
            # Display structured data
            st.json(st.session_state.structured_data)
            
            # Download button for JSON
            json_str = json.dumps(st.session_state.structured_data, indent=2)
            st.download_button(
                label="Download JSON",
                data=json_str,
                file_name="structured_data.json",
                mime="application/json"
            )
