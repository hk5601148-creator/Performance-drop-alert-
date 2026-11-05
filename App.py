
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
st.write("Monitor student performance and identify students who need support.")

# Risk prediction
def predict_risk(attendance, marks):
    if attendance < 60 and marks < 40:
        return "High", "Attendance below 60% and internal marks below 40%"

    elif attendance < 75 or marks < 50:
        reasons = []
        if attendance < 75:
            reasons.append("Attendance below 75%")
        if marks < 50:
            reasons.append("Internal marks below 50%")
        return "Medium", " and ".join(reasons)

    else:
        return "Low", "Attendance and internal marks are satisfactory"


# Email alert
def send_alert(name, roll, reason):
    try:
        email_settings = st.secrets["email"]

        msg = EmailMessage()
        msg["Subject"] = "High Risk Student Alert"
        msg["From"] = email_settings["sender"]
        msg["To"] = email_settings["recipient"]

        msg.set_content(
            f"Dear Teacher,\n\n"
            f"Student Name: {name}\n"
            f"Roll Number: {roll}\n"
            f"Risk Level: High\n"
            f"Reason: {reason}\n\n"
            f"Please arrange a meeting and prepare an improvement plan."
        )

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(
                email_settings["sender"],
                email_settings["password"]
            )
            server.send_message(msg)

        return True

    except Exception as e:
        st.error(f"Email could not be sent: {e}")
        return False


# Session storage
if "students" not in st.session_state:
    st.session_state.students = pd.DataFrame(columns=[
        "Roll Number",
        "Student Name",
        "Attendance",
        "Internal Marks",
        "Previous semester",
        "Risk Level",
        "Reason"
    ])

df = st.session_state.students.copy()

# Add student
st.header("➕ Add Student")

with st.form("student_form"):
    roll = st.text_input("Roll Number")
    name = st.text_input("Student Name")
    attendance = st.number_input("Attendance (%)", 0.0, 100.0, 80.0)
    marks = st.number_input("Internal Marks", 0.0, 100.0, 60.0)
    previous = st.number_input("Previous semester (%)", 0.0, 100.0, 60.0)

    submitted = st.form_submit_button("Add Student")

    if submitted:
        if not roll.strip() or not name.strip():
            st.warning("Please enter both roll number and student name.")

        elif roll.strip() in st.session_state.students["Roll Number"].astype(str).values:
            st.warning("This roll number already exists.")

        else:
            risk, reason = predict_risk(attendance, marks)

            new_student = pd.DataFrame([{
                "Roll Number": roll.strip(),
                "Student Name": name.strip(),
                "Attendance": attendance,
                "Internal Marks": marks,
                "Previous semester": previous,
                "Risk Level": risk,
                "Reason": reason
            }])

            st.session_state.students = pd.concat(
                [st.session_state.students, new_student],
                ignore_index=True
            )

            if risk == "High":
                if "email" in st.secrets:
                    if send_alert(name, roll, reason):
                        st.success("Student added. High-risk email alert sent!")
                else:
                    st.warning("Student added, but email settings are missing.")
            else:
                st.success(f"Student added successfully. Risk Level: {risk}")

            st.rerun()


# Dashboard
st.header("📊 Performance Dashboard")

df = st.session_state.students.copy()

if not df.empty:
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Students", len(df))
    col2.metric("High Risk", int((df["Risk Level"] == "High").sum()))
    col3.metric("Medium Risk", int((df["Risk Level"] == "Medium").sum()))
    col4.metric("Low Risk", int((df["Risk Level"] == "Low").sum()))

    st.subheader("Risk Distribution")

    counts = df["Risk Level"].value_counts().reindex(
        ["High", "Medium", "Low"], fill_value=0
    )

    chart_data = pd.DataFrame({
        "Risk Level": counts.index,
        "Students": counts.values
    })

    fig = px.pie(
        chart_data,
        names="Risk Level",
        values="Students",
        title="Student Risk Levels"
    )

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Student Records")
    st.dataframe(df, use_container_width=True)

    st.subheader("⚠️ Students Needing Attention")

    high_risk = df[df["Risk Level"] == "High"]

    if not high_risk.empty:
        st.dataframe(high_risk, use_container_width=True)
    else:
        st.success("No high-risk students currently.")

    st.download_button(
        "Download Student Report",
        df.to_csv(index=False).encode("utf-8"),
        "student_performance_report.csv",
        "text/csv"
    )

else:
    st.info("No students added yet. Use the form above to add student records.")
