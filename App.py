import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(
    page_title="Performance Drop Alert",
    page_icon="📊",
    layout="wide"
)

FILE = "students.csv"

st.title("📊 Student Performance Drop Alert System")
st.write(
    "A system to monitor student attendance, marks "
    "and previous semester performance."
)

# Sample student data
def load_data():
    if os.path.exists(FILE):
        data = pd.read_csv(FILE)
    else:
        data = pd.DataFrame({
            "Roll Number": ["101", "102", "103", "104", "105"],
            "Student Name": ["Aman", "Simran", "Rahul", "Priya", "Karan"],
            "Attendance": [55, 85, 70, 92, 45],
            "Internal Marks": [30, 75, 45, 88, 25],
            "Previous Semester %": [48, 82, 60, 90, 42]
        })
    return data


df = load_data()

# Risk prediction
def predict_risk(row):
    attendance = float(row["Attendance"])
    marks = float(row["Internal Marks"])
    previous = float(row["Previous semester"])
    
    if attendance < 60 and marks < 40:
    def predict_risk(row):
    attendance = float(row["Attendance"])
    marks = float(row["Internal Marks"])
    previous = float(row["Previous semester"])

    if attendance < 60 and marks < 40:
        risk = "High"
        reason = "Low attendance and low internal marks"
    elif previous < 40:
        risk = "High"
        reason = "Low previous semester percentage"
    elif attendance < 75 or marks < 50 or previous < 50:
        risk = "Medium"
        reason = "Needs improvement in academic performance"
    else:
        risk = "Low"
        reason = "Good academic performance"

    return pd.Series([
            "High",
            "Attendance below 60% and marks below 40."
        ])

    elif attendance < 75 or marks < 50:
        reasons = []

        if attendance < 75:
            reasons.append("Attendance below 75%")

        if marks < 50:
            reasons.append("Internal marks below 50")

        return pd.Series([
            "Medium",
            " and ".join(reasons) + "."
        ])
    


df[["Risk Level", "Risk Reason"]] = df.apply(
    predict_risk,
    axis=1
)

# Dashboard
st.header("📌 Performance Dashboard")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Total Students", len(df))
col2.metric("High Risk", len(df[df["Risk Level"] == "High"]))
col3.metric("Medium Risk", len(df[df["Risk Level"] == "Medium"]))
col4.metric("Low Risk", len(df[df["Risk Level"] == "Low"]))

# Student records
st.header("👩‍🎓 Student Records")
st.dataframe(df, use_container_width=True)

# Risk analysis chart
st.header("📈 Student Risk Analysis")

risk_count = (
    df["Risk Level"]
    .value_counts()
    .reindex(["High", "Medium", "Low"], fill_value=0)
    .rename_axis("Risk Level")
    .reset_index(name="Students")
)

fig = px.pie(
    risk_count,
    names="Risk Level",
    values="Students",
    title="Students by Risk Level"
)

st.plotly_chart(fig, use_container_width=True)

# Risk alerts
st.header("🚨 Performance Alerts")

for _, student in df.iterrows():

    message = (
        f'{student["Student Name"]} - '
        f'{student["Risk Level"]} Risk: '
        f'{student["Risk Reason"]}'
    )

    if student["Risk Level"] == "High":
        st.error(message)

    elif student["Risk Level"] == "Medium":
        st.warning(message)

    else:
        st.success(message)

# Add new student
st.header("➕ Add New Student")

with st.form("student_form"):

    roll = st.text_input("Roll Number")
    name = st.text_input("Student Name")

    attendance = st.number_input(
        "Attendance (%)",
        min_value=0.0,
        max_value=100.0,
        value=0.0
    )

    marks = st.number_input(
        "Internal Marks",
        min_value=0.0,
        max_value=100.0,
        value=0.0
    )

    previous = st.number_input(
        "Previous Semester (%)",
        min_value=0.0,
        max_value=100.0,
        value=0.0
    )

    submitted = st.form_submit_button("Add Student")

    if submitted:

        if not roll.strip() or not name.strip():
            st.error("Please enter roll number and student name.")

        elif roll.strip() in df["Roll Number"].astype(str).values:
            st.error("This roll number already exists.")

        else:

            new_student = pd.DataFrame([{
                "Roll Number": roll.strip(),
                "Student Name": name.strip(),
                "Attendance": attendance,
                "Internal Marks": marks,
                "Previous Semester %": previous
            }])

            saved_data = pd.concat([
                df[[
                    "Roll Number",
                    "Student Name",
                    "Attendance",
                    "Internal Marks",
                    "Previous Semester %"
                ]],
                new_student
            ], ignore_index=True)

            saved_data.to_csv(FILE, index=False)

            st.success("Student added successfully!")
            st.rerun()

# Automatic email alert for high-risk students
import smtplib
from email.message import EmailMessage

def send_alert(student):
    try:
        sender = st.secrets["email"]["sender"]
        password = st.secrets["email"]["password"]
        recipient = st.secrets["email"]["recipient"]

        message = EmailMessage()
        message["Subject"] = "High Risk Student Alert"
        message["From"] = sender
        message["To"] = recipient

        message.set_content(
            f"""
            High Risk Student Alert

            Roll Number: {student['Roll Number']}
            Student Name: {student['Student Name']}
            Attendance: {student['Attendance']}%
            Internal Marks: {student['Internal Marks']}

            Risk Reason: {student['Risk Reason']}
            """
        )

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender, password)
            server.send_message(message)

        return True

    except Exception as error:
        st.error(f"Email could not be sent: {error}")
        return False


st.header("📧 High Risk Email Alerts")

if st.button("Send High Risk Email Alerts"):
    high_risk_students = df[df["Risk Level"] == "High"]

    if high_risk_students.empty:
        st.info("There are no high-risk students.")
    else:
        for _, student in high_risk_students.iterrows():
            if send_alert(student):
                st.success(
                    f"Alert email sent for {student['Student Name']}."
    )
    
    
