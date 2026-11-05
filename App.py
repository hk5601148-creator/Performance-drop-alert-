
import streamlit as st
import pandas as pd
import smtplib
from email.message import EmailMessage
from google import genai

st.set_page_config(
    page_title="Performance Drop Alert",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Student Performance Drop Alert")
st.write("Monitor student performance and identify students who need support.")

# Temporary app storage
if "students" not in st.session_state:
    st.session_state.students = pd.DataFrame(columns=[
        "Roll", "Name", "Attendance %",
        "Internal Marks", "Previous Semester %",
        "Risk Level", "Reason"
    ])

def analyse_student(attendance, internal):
    if attendance < 60 and internal < 40:
        risk = "High Risk"
    elif attendance < 75 or internal < 50:
        risk = "Medium Risk"
    else:
        risk = "Low Risk"

    reason = (
        f"Attendance is {attendance}% and internal marks are {internal}%. "
    )

    if risk == "High Risk":
        reason += "Both attendance and internal marks are critically low."
    elif risk == "Medium Risk":
        reason += "Attendance or internal marks need improvement."
    else:
        reason += "Attendance and internal marks are satisfactory."

    # Ask Gemini to improve the explanation
    try:
        api_key = st.secrets["gemini"]["api_key"]
        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=(
                f"Explain this student's {risk} status in one simple sentence. "
                f"Attendance: {attendance}%. Internal marks: {internal}%. "
                f"Use these exact risk rules: High Risk if attendance <60 "
                f"AND internal marks <40; Medium Risk if attendance <75 "
                f"OR internal marks <50; otherwise Low Risk. "
                f"Do not change the risk category."
            )
        )

        if response.text:
            reason = response.text.strip()

    except Exception:
        pass

    return risk, reason


def send_alert(name, reason):
    try:
        sender = st.secrets["email"]["sender_email"]
        password = st.secrets["email"]["app_password"]
        recipient = st.secrets["email"]["recipient_email"]

        message = EmailMessage()
        message["Subject"] = f"High Risk Student Alert: {name}"
        message["From"] = sender
        message["To"] = recipient
        message.set_content(
            f"Dear {name},\n\n"
            f"You are at risk due to: {reason}\n\n"
            "Please meet your mentor and prepare an improvement plan."
        )

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.send_message(message)

        return True

    except Exception as error:
        st.error(f"Email could not be sent: {error}")
        return False


# Student entry
st.header("Add Student Details")

with st.form("student_form"):
    roll = st.text_input("Roll Number")
    name = st.text_input("Student Name")
    attendance = st.number_input(
        "Attendance %", min_value=0.0, max_value=100.0, value=80.0
    )
    internal = st.number_input(
        "Internal Marks", min_value=0.0, max_value=100.0, value=60.0
    )
    previous = st.number_input(
        "Previous Semester %", min_value=0.0,
        max_value=100.0, value=70.0
    )

    submitted = st.form_submit_button("Analyse and Add Student")

if submitted:
    if not roll.strip() or not name.strip():
        st.warning("Please enter both Roll Number and Student Name.")
    elif roll.strip() in st.session_state.students["Roll"].astype(str).values:
        st.warning("This Roll Number already exists.")
    else:
        risk, reason = analyse_student(attendance, internal)

        new_student = {
            "Roll": roll.strip(),
            "Name": name.strip(),
            "Attendance %": attendance,
            "Internal Marks": internal,
            "Previous Semester %": previous,
            "Risk Level": risk,
            "Reason": reason
        }

        st.session_state.students = pd.concat(
            [st.session_state.students, pd.DataFrame([new_student])],
            ignore_index=True
        )

        st.success(f"Student added successfully: {risk}")

        if risk == "High Risk":
            if st.button("Send High Risk Email", key=f"send_{roll}"):
                if send_alert(name, reason):
                    st.success("Email alert sent successfully!")


# Dashboard
st.header("Performance Dashboard")

df = st.session_state.students

if not df.empty:
    high = (df["Risk Level"] == "High Risk").sum()
    medium = (df["Risk Level"] == "Medium Risk").sum()
    low = (df["Risk Level"] == "Low Risk").sum()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Students", len(df))
    col2.metric("High Risk", int(high))
    col3.metric("Medium Risk", int(medium))
    col4.metric("Low Risk", int(low))

    st.subheader("Risk Distribution")
    chart_data = pd.DataFrame({
        "Risk Level": ["High Risk", "Medium Risk", "Low Risk"],
        "Students": [high, medium, low]
    }).set_index("Risk Level")

    st.bar_chart(chart_data)

    st.subheader("Student Records")
    st.dataframe(df, use_container_width=True)

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download Student Records (CSV)",
        data=csv,
        file_name="student_records.csv",
        mime="text/csv"
    )

else:
    st.info("No students added yet. Enter student details above to begin.")

st.caption("Performance Drop Alert | Student Monitoring System")
