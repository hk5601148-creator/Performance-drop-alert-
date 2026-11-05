
import streamlit as st
import pandas as pd
import plotly.express as px
import smtplib
from email.message import EmailMessage

st.set_page_config(
    page_title="Performance Drop Alert",
    page_icon="🎓",
    layout="wide"
)

st.title("🎓 Student Performance Drop Alert")
st.write("A simple system to identify students who may need academic support.")

COLUMNS = [
    "Roll Number",
    "Student Name",
    "Attendance",
    "Internal Marks",
    "Previous semester",
    "Risk Level",
    "Reason"
]

# Risk prediction
def predict_risk(attendance, marks, previous):
    if (attendance < 60 and marks < 40) or previous < 40:
        return "High", "Very low attendance, marks, or previous semester percentage"

    elif attendance < 75 or marks < 50 or previous < 50:
        return "Medium", "Needs improvement in academic performance"

    else:
        return "Low", "Good academic performance"


# Sample student records
sample_data = [
    ["101", "Aman", 90, 85, 82, "Low", "Good academic performance"],
    ["102", "Simran", 70, 65, 72, "Medium", "Needs improvement in academic performance"],
    ["103", "Rahul", 55, 35, 60, "High", "Very low attendance, marks, or previous semester percentage"],
    ["104", "Priya", 80, 75, 85, "Low", "Good academic performance"],
    ["105", "Karan", 68, 45, 48, "Medium", "Needs improvement in academic performance"],
    ["106", "Neha", 85, 88, 35, "High", "Very low attendance, marks, or previous semester percentage"]
]

if "students" not in st.session_state:
    st.session_state.students = pd.DataFrame(
        sample_data, columns=COLUMNS
    )


# Email alert
def send_alert(name, roll, reason):
    try:
        settings = st.secrets["email"]

        message = EmailMessage()
        message["Subject"] = "High Risk Student Alert"
        message["From"] = settings["sender"]
        message["To"] = settings["recipient"]

        message.set_content(
            f"High Risk Student Alert\n\n"
            f"Student Name: {name}\n"
            f"Roll Number: {roll}\n"
            f"Reason: {reason}\n\n"
            "Please provide academic support to this student."
        )

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(settings["sender"], settings["password"])
            server.send_message(message)

        return True

    except Exception:
        st.error("Email could not be sent. Please check your email settings.")
        return False


# Add student
st.header("➕ Add New Student")

with st.form("student_form"):
    roll = st.text_input("Roll Number")
    name = st.text_input("Student Name")
    attendance = st.number_input("Attendance (%)", 0.0, 100.0, 80.0)
    marks = st.number_input("Internal Marks", 0.0, 100.0, 60.0)
    previous = st.number_input("Previous semester (%)", 0.0, 100.0, 60.0)

    submitted = st.form_submit_button("Add Student")

    if submitted:
        existing_rolls = st.session_state.students["Roll Number"].astype(str)

        if not roll.strip() or not name.strip():
            st.warning("Please enter the roll number and student name.")

        elif roll.strip() in existing_rolls.values:
            st.warning("This roll number already exists.")

        else:
            risk, reason = predict_risk(
                attendance, marks, previous
            )

            new_row = pd.DataFrame([{
                "Roll Number": roll.strip(),
                "Student Name": name.strip(),
                "Attendance": attendance,
                "Internal Marks": marks,
                "Previous semester": previous,
                "Risk Level": risk,
                "Reason": reason
            }])

            st.session_state.students = pd.concat(
                [st.session_state.students, new_row],
                ignore_index=True
            )

            if risk == "High":
                if "email" in st.secrets:
                    if send_alert(name, roll, reason):
                        st.success("Student added and email alert sent!")
                else:
                    st.warning("Student added, but email settings are missing.")
            else:
                st.success(f"Student added successfully. Risk: {risk}")

            st.rerun()


# Dashboard
st.header("📊 Dashboard")

df = st.session_state.students.copy()

total = len(df)
high = int((df["Risk Level"] == "High").sum())
medium = int((df["Risk Level"] == "Medium").sum())
low = int((df["Risk Level"] == "Low").sum())

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Students", total)
c2.metric("High Risk", high)
c3.metric("Medium Risk", medium)
c4.metric("Low Risk", low)

# Pie chart
st.subheader("Risk Distribution")

chart_data = pd.DataFrame({
    "Risk Level": ["High", "Medium", "Low"],
    "Students": [high, medium, low]
})

fig = px.pie(
    chart_data,
    names="Risk Level",
    values="Students",
    title="Student Risk Levels"
)

st.plotly_chart(fig, use_container_width=True)

# Student table
st.subheader("📋 Student Records")
st.dataframe(df, use_container_width=True, hide_index=True)

# High-risk list
st.subheader("⚠️ High Risk Students")

high_students = df[df["Risk Level"] == "High"]

if not high_students.empty:
    st.dataframe(high_students, use_container_width=True, hide_index=True)
else:
    st.success("No high-risk students.")

# Download report
st.subheader("Download Report")

st.download_button(
    label="Download Student Report",
    data=df.to_csv(index=False).encode("utf-8"),
    file_name="student_performance_report.csv",
    mime="text/csv"
    )
    
