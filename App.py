
import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google import genai
import json
import smtplib
from email.message import EmailMessage

st.set_page_config(page_title="Performance Drop Alert", page_icon="🎓", layout="wide")

st.title("🎓 Performance Drop Alert")
st.write("Student performance monitoring and early risk identification")

# Connect Google Sheets
@st.cache_resource
def connect_sheet():
    credentials = dict(st.secrets["gcp_service_account"])
    gc = gspread.service_account_from_dict(credentials)
    return gc.open_by_url(st.secrets["google_sheet"]["url"]).sheet1

# Gemini risk prediction
def predict_risk(attendance, marks):
    prompt = f"""
You are a student performance risk analyser.

Attendance: {attendance}%
Internal Marks: {marks}

Follow these exact rules:
1. If attendance <60% AND internal marks <40: High Risk.
2. If attendance <75% OR internal marks <50: Medium Risk.
3. Otherwise: Low Risk.

Give a short reason.

Return only JSON in this format:
{{"risk_level": "High", "reason": "Your reason"}}
"""
    client = genai.Client(api_key=st.secrets["gemini"]["api_key"])
    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=prompt,
        config={"response_mime_type": "application/json"}
    )
    result = json.loads(response.text)

    if result["risk_level"] not in ["High", "Medium", "Low"]:
        raise ValueError("Gemini returned an invalid risk level.")

    return result["risk_level"], result["reason"]

# Email alert
def send_email(name, reason):
    settings = st.secrets["email"]
    msg = EmailMessage()
    msg["Subject"] = "Student Performance Risk Alert"
    msg["From"] = settings["sender"]
    msg["To"] = settings["recipient"]
    msg.set_content(
        f"Dear {name},\n\n"
        f"You are at risk due to: {reason}\n\n"
        "Please meet your mentor and prepare an improvement plan.\n\n"
        "Regards,\nStudent Performance Alert System"
    )

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(settings["sender"], settings["password"])
        server.send_message(msg)

# Load sheet
try:
    sheet = connect_sheet()
    records = sheet.get_all_records()
    df = pd.DataFrame(records)
except Exception as e:
    st.error("Could not connect to Google Sheets. Check your Secrets and sheet access.")
    st.stop()

required = [
    "Roll", "Name", "Attendance %",
    "Internal Marks", "Previous Semester %"
]

if not all(column in df.columns for column in required):
    st.error("Your Google Sheet must contain: " + ", ".join(required))
    st.stop()

# Add missing output columns
for column in ["Risk Level", "Reason"]:
    if column not in df.columns:
        sheet.update_cell(1, len(df.columns) + 1, column)
        df[column] = ""

# Add student
st.header("Add Student")

with st.form("student_form"):
    roll = st.text_input("Roll Number")
    name = st.text_input("Student Name")
    attendance = st.number_input("Attendance %", 0.0, 100.0, 80.0)
    marks = st.number_input("Internal Marks", 0.0, 100.0, 60.0)
    previous = st.number_input("Previous Semester %", 0.0, 100.0, 60.0)

    add = st.form_submit_button("Add Student")

if add:
    if not roll.strip() or not name.strip():
        st.warning("Enter roll number and student name.")
    elif any(str(r.get("Roll")) == roll.strip() for r in records):
        st.warning("This roll number already exists.")
    else:
        try:
            risk, reason = predict_risk(attendance, marks)

            sheet.append_row([
                roll.strip(), name.strip(), attendance,
                marks, previous, risk, reason
            ])

            if risk == "High":
                try:
                    send_email(name, reason)
                    st.success("Student added and high-risk email sent.")
                except Exception:
                    st.warning("Student added, but email could not be sent.")

            else:
                st.success(f"Student added. Risk Level: {risk}")

            st.rerun()

        except Exception as e:
            st.error(f"Could not analyse student: {e}")

# Analyse existing students
st.header("Gemini Risk Analysis")

if st.button("Analyse all students with Gemini"):
    try:
        current_records = sheet.get_all_records()

        for row_number, row in enumerate(current_records, start=2):
            risk, reason = predict_risk(
                float(row["Attendance %"]),
                float(row["Internal Marks"])
            )
            sheet.update(
                range_name=f"F{row_number}:G{row_number}",
                values=[[risk, reason]]
            )

        st.success("Risk Level and Reason updated in Google Sheets.")
        st.rerun()

    except Exception as e:
        st.error(f"Analysis failed: {e}")

# Dashboard
st.header("Performance Dashboard")

try:
    df = pd.DataFrame(sheet.get_all_records())

    if not df.empty:
        for column in ["Risk Level", "Reason"]:
            if column not in df.columns:
                df[column] = ""

        high = int((df["Risk Level"] == "High").sum())
        medium = int((df["Risk Level"] == "Medium").sum())
        low = int((df["Risk Level"] == "Low").sum())

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Students", len(df))
        c2.metric("High Risk", high)
        c3.metric("Medium Risk", medium)
        c4.metric("Low Risk", low)

        chart = pd.DataFrame({
            "Risk Level": ["High", "Medium", "Low"],
            "Students": [high, medium, low]
        })

        st.subheader("Risk Distribution")
        fig = px.pie(chart, names="Risk Level", values="Students")
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Student List")
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.subheader("High Risk Students")
        st.dataframe(
            df[df["Risk Level"] == "High"],
            use_container_width=True,
            hide_index=True
        )

        st.download_button(
            "Download Student Report",
            df.to_csv(index=False).encode("utf-8"),
            "student_report.csv",
            "text/csv"
        )
    else:
        st.info("Your Google Sheet has no student records yet.")

except Exception as e:
    st.error(f"Dashboard could not load: {e}")
