import streamlit as st
import google.generativeai as genai
from PIL import Image
from io import BytesIO  # Import BytesIO
import re 
# Replace with your actual API key (securely in a real application)
GOOGLE_API_KEY = "AIzaSyDG-Uedfxsuv6owHP55XkpgNuvQfwVXw5s" # **Replace this!**
genai.configure(api_key=GOOGLE_API_KEY)

# Gold prices per gram in INR (Indian Rupees)
GOLD_PRICES_INR = {
    "24K": 8634,
    "22K": 7915,
    "20K": 7195,
    "18K": 6476,
    "16K": 5756,
    "14K": 5037,
    "12K": 4317,
    "10K": 3598,
}

DIAMOND_PRICES_INR = {
    "0.3-1.0": 35000,
    "1.1-2.1": 50000,
    "2.1-3.0": 70000,
}

DEFAULT_GOLD_KARAT = "22K" # Default karat if not specified in analysis

# Static Exchange Rates (as of Oct 26, 2023 - Replace with real-time rates for production)
EXCHANGE_RATES = {
    "USD": 0.012,  # INR to USD
    "CAD": 0.016,  # INR to CAD
    "INR": 1.0     # INR to INR (base rate)
}

def convert_currency(price_inr, to_currency):
    if to_currency in EXCHANGE_RATES:
        return price_inr * EXCHANGE_RATES[to_currency]
    else:
        return price_inr # Default to INR if currency not supported


def analyze_jewelry(image_file, target_currency="INR"):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')

        if image_file is None:
            return "Error: No image file uploaded.", None

        try:
            pil_image = Image.open(image_file)
            buffered = BytesIO()
            pil_image.save(buffered, format="JPEG")
            image_bytes = buffered.getvalue()

            if not image_bytes:
                return "Error: Could not get image bytes from PIL.", None
            else:
                print(f"Image bytes obtained from PIL successfully! Size: {len(image_bytes)} bytes")

                image_parts = [
                    {"mime_type": "image/jpeg", "data": image_bytes}
                ]
        except Exception as pil_error:
            return f"Error during image processing with PIL: {pil_error}", None

        prompt_parts = [
            "Analyze this jewelry image. Assume the jewelry is always made of gold (it can be yellow gold, white gold, or rose gold).",
            "Provide a concise analysis. Tell me:", # Request concise analysis
            "\n1. What type of jewelry is it? (e.g., ring, earring, necklace, bracelet)",
            "\n2. Briefly describe the jewelry's materials and design.", # Request brief description
            "\n3. Estimate the approximate amount of gold used (in grams) and the total carat weight of diamonds (if any). Provide numerical ranges or single numbers if possible.", # Clear estimation request
            "\n\nRemember these are visual estimations and not precise measurements.",
            image_parts[0], # The image data
        ]

        response = model.generate_content(prompt_parts)
        response.resolve()

        if response.text:
            analysis_text = response.text
            estimated_price_inr = calculate_estimated_price(analysis_text)
            estimated_price_converted = convert_currency(estimated_price_inr, target_currency) # Convert to selected currency
            return analysis_text, estimated_price_converted
        else:
            return "Sorry, I couldn't analyze the image effectively. Please try again with a clearer image.", None

    except Exception as e:
        return f"Error during analysis: {e}", None


def calculate_estimated_price(analysis_text):
    diamond_carat = 0.0
    gold_weight_grams = 0.0

    diamond_match = re.search(r"diamond.*?(\d+\.?\d*)\s*carat", analysis_text, re.IGNORECASE)
    if diamond_match:
        try:
            diamond_carat = float(diamond_match.group(1))
        except ValueError:
            print("Could not parse diamond carat value.")

    diamond_price_inr = 0
    if 0.3 <= diamond_carat <= 1.0:
        diamond_price_inr = DIAMOND_PRICES_INR["0.3-1.0"]
    elif 1.1 <= diamond_carat <= 2.1:
        diamond_price_inr = DIAMOND_PRICES_INR["1.1-2.1"]
    elif 2.1 <= diamond_carat <= 3.0:
        diamond_price_inr = DIAMOND_PRICES_INR["2.1-3.0"]
    elif diamond_carat > 3.0:
        diamond_price_inr = DIAMOND_PRICES_INR["2.1-3.0"] * (diamond_carat / 2.5) # Rough scaling above 3 carat

    gold_weight_match = re.search(r"gold.*?(\d+)\s*-\s*(\d+)\s*grams", analysis_text, re.IGNORECASE)
    if gold_weight_match:
        try:
            gold_weight_grams = (float(gold_weight_match.group(1)) + float(gold_weight_match.group(2))) / 2
        except ValueError:
            print("Could not parse gold weight range.")
    else:
        gold_weight_match_single = re.search(r"gold.*?around\s*(\d+)\s*grams", analysis_text, re.IGNORECASE)
        if gold_weight_match_single:
            try:
                gold_weight_grams = float(gold_weight_match_single.group(1))
            except ValueError:
                print("Could not parse single gold weight.")
        elif re.search(r"substantial amount of gold", analysis_text, re.IGNORECASE):
            gold_weight_grams = 15
        elif re.search(r"minimal gold", analysis_text, re.IGNORECASE):
            gold_weight_grams = 5
        else:
            gold_weight_grams = 10

    gold_karat_match = re.search(r"(\d{2})K\s*gold", analysis_text, re.IGNORECASE)
    gold_karat = DEFAULT_GOLD_KARAT
    if gold_karat_match:
        karat_value = gold_karat_match.group(1)
        if karat_value + "K" in GOLD_PRICES_INR:
            gold_karat = karat_value + "K"

    gold_price_inr = gold_weight_grams * GOLD_PRICES_INR[gold_karat] if gold_weight_grams > 0 else 0

    total_price_inr = diamond_price_inr + gold_price_inr
    return int(total_price_inr)


# Streamlit App UI - Enhanced UI
st.set_page_config(page_title="Jewelry Analyzer & Price Estimator")
st.title("Jewelry Image Analyzer & Price Estimator")

st.sidebar.header("App Settings")
currency_option = st.sidebar.selectbox("Select Currency", ["INR (₹)", "USD ($)", "CAD ($)"], index=0) # Added USD and CAD

st.write("Upload an image of your jewelry to get a concise analysis and approximate price estimation.") # Updated description for conciseness
st.write("Please note: Price estimations are visual approximations and are **per jewelry item shown in the image**.") # Clarified price per item

col1, col2 = st.columns([1, 1])

with col1:
    uploaded_file = st.file_uploader("Choose a jewelry image (JPG, JPEG, PNG)", type=["jpg", "jpeg", "png"])
    if uploaded_file is not None:
        st.image(Image.open(uploaded_file), caption="Uploaded Jewelry Image.", use_container_width=True)

with col2:
    if uploaded_file is not None:
        st.subheader("Image Details")
        st.write(f"**File name:** {uploaded_file.name}")
        st.write(f"**File type:** {uploaded_file.type}")
        st.write(f"**File size:** {uploaded_file.size} bytes")

        if st.button("Analyze Image"):
            with st.spinner("Analyzing jewelry image..."):
                analysis_text, estimated_price_converted = analyze_jewelry(uploaded_file, currency_option[:3]) # Pass currency code

            st.subheader("Analysis Result:")
            if "Error" in analysis_text:
                st.error(analysis_text)
                st.write("Please try again with a clearer image or different image.")
            else:
                st.success("Analysis complete!")
                with st.expander("Detailed Analysis"): # Still using expander, but should be more concise now
                    st.write(analysis_text)

                if estimated_price_converted is not None:
                    st.subheader("Estimated Price (Approximate):")
                    currency_symbol = currency_option.split(' ')[-1][1] # Extract currency symbol from dropdown
                    st.metric(label="Estimated Price (per item)", value=f"{currency_symbol} {estimated_price_converted:,.2f}") # Updated label, dynamic currency symbol
                else:
                    st.warning("Could not estimate price based on analysis.")