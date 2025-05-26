import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import gradio as gr
import nltk
from nltk.tokenize import word_tokenize
import re

# ดาวน์โหลดทั้ง punkt และ punkt_tab
nltk.download('punkt')
nltk.download('punkt_tab')

def load_data():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open("PropertyData").sheet1
    data = sheet.get_all_records()
    return pd.DataFrame(data)

def parse_query(query):
    query = query.lower()
    tokens = word_tokenize(query)
    result = {"property_type": None, "bedrooms": None, "price_max": None, "location": None, "status": "available"}

    for token in tokens:
        if "บ้านเดี่ยว" in token or "บ้าน" in token:
            result["property_type"] = "บ้านเดี่ยว"
        elif "คอนโด" in token:
            result["property_type"] = "คอนโด"
        elif "ทาวน์โฮม" in token:
            result["property_type"] = "ทาวน์โฮม"

        if re.search(r"(\d+)\s*ห้องนอน|(\d+)\s*bedroom", token):
            num = re.search(r"\d+", token).group()
            result["bedrooms"] = int(num)

        if "ไม่เกิน" in query or "under" in query:
            match = re.search(r"ไม่เกิน\s*(\d+(?:\.\d+)?)\s*ล้าน|under\s*(\d+(?:\.\d+)?)", query)
            if match:
                amount = float(match.group(1) or match.group(2)) * 1_000_000 if "ล้าน" in query else float(match.group(1) or match.group(2))
                result["price_max"] = amount

        if "นนทบุรี" in token:
            result["location"] = "นนทบุรี"
        elif "กรุงเทพ" in token:
            result["location"] = "กรุงเทพ"

        if "reserved" in query or "จอง" in query:
            result["status"] = "reserved"

    return result

def search_property(query):
    query_params = parse_query(query)
    df = load_data()

    result = df[df["status"] == query_params["status"]]

    if query_params["property_type"]:
        result = result[result["property_type"].str.lower() == query_params["property_type"].lower()]
    if query_params["bedrooms"]:
        result = result[result["bedrooms"] == query_params["bedrooms"]]
    if query_params["price_max"]:
        result = result[result["price"] <= query_params["price_max"]]
    if query_params["location"]:
        result = result[result["location"].str.contains(query_params["location"])]

    return result.reset_index(drop=True)

iface = gr.Interface(
    fn=search_property,
    inputs=gr.Textbox(label="Customer Query", placeholder="เช่น บ้านเดี่ยว 2 ห้องนอน ไม่เกิน 3 ล้าน ในนนทบุรี"),
    outputs=gr.Dataframe(label="Recommended Properties"),
    title="แนะนำทรัพย์อสังหาอัตโนมัติ",
    description="ใส่ความต้องการลูกค้า → ระบบจะเลือกทรัพย์ตามสถานะ (Available/Reserved)"
)

iface.launch()