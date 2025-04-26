import streamlit as st
import requests
from bs4 import BeautifulSoup
import json
import google.generativeai as genai
import PyPDF2
import io

st.title("Content Scraper & Structured Extractor")
st.write("Extract structured data from websites or PDFs using Gemini")

if 'scraped_content' not in st.session_state:
    st.session_state.scraped_content = ""
if 'structured_data' not in st.session_state:
    st.session_state.structured_data = {}

gemini_api_key = st.sidebar.text_input("Enter Google Gemini API Key:", type="password")
if gemini_api_key:
    genai.configure(api_key=gemini_api_key)

content_source = st.radio("Select content source:", ("Website URL", "PDF File"))

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
        page_title = soup.title.string if soup.title else "No title found"
        return text, page_title
    except Exception as e:
        return f"Error: {str(e)}", "Error"

def extract_text_from_pdf(uploaded_file):
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(uploaded_file.read()))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text, uploaded_file.name
    except Exception as e:
        return f"Error: {str(e)}", "Error"

def extract_structured_data_with_gemini(text, source_name):
    if not gemini_api_key:
        return {"error": "Please enter your Google Gemini API key in the sidebar"}
    max_length = 30000
    truncated_text = text[:max_length] if len(text) > max_length else text
    prompt = f"""
    Extract structured information from the following {source_name} content.
    
    SOURCE: {source_name}
    CONTENT: 
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

        Focus only on relevant card details. Ignore unrelated text.
    """
    try:
        model = genai.GenerativeModel('models/gemini-1.5-pro')
        response = model.generate_content(prompt)
        result = response.text
        try:
            result = result.replace("```json", "").replace("```", "").strip()
            structured_data = json.loads(result)
            return structured_data
        except json.JSONDecodeError:
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

tab1, tab2 = st.tabs(["Content Extractor", "Structured Data"])

with tab1:
    if content_source == "Website URL":
        url = st.text_input("Enter URL:", "https://example.com")
        if st.button("Scrape Content"):
            with st.spinner("Scraping content..."):
                st.session_state.scraped_content, page_title = scrape_url(url)
                if not st.session_state.scraped_content.startswith("Error"):
                    st.success("Content scraped successfully!")
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
    else:
        uploaded_file = st.file_uploader("Upload PDF file", type=["pdf"])
        if uploaded_file and st.button("Extract PDF Content"):
            with st.spinner("Extracting text from PDF..."):
                st.session_state.scraped_content, file_name = extract_text_from_pdf(uploaded_file)
                if not st.session_state.scraped_content.startswith("Error"):
                    st.success("PDF content extracted successfully!")
                    if gemini_api_key:
                        with st.spinner("Extracting structured data with Gemini..."):
                            st.session_state.structured_data = extract_structured_data_with_gemini(
                                st.session_state.scraped_content, 
                                file_name
                            )
                        st.success("Structured extraction complete!")
                    else:
                        st.warning("Enter Google Gemini API key in sidebar to extract structured data")
                else:
                    st.error(st.session_state.scraped_content)

    if st.session_state.scraped_content and not st.session_state.scraped_content.startswith("Error"):
        st.subheader("Extracted Content")
        st.text_area("Content", st.session_state.scraped_content, height=300)

with tab2:
    if st.session_state.structured_data:
        st.subheader("Structured Data Extracted by Gemini")
        if "error" in st.session_state.structured_data:
            st.error(f"Error: {st.session_state.structured_data['error']}")
            if "raw_response" in st.session_state.structured_data:
                st.text_area("Raw Gemini Response", st.session_state.structured_data["raw_response"], height=200)
        else:
            st.json(st.session_state.structured_data)
            json_str = json.dumps(st.session_state.structured_data, indent=2)
            st.download_button(
                label="Download JSON",
                data=json_str,
                file_name="structured_data.json",
                mime="application/json"
            )
