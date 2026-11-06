import re
import time
import smtplib
from email.message import EmailMessage

import streamlit as st
import pandas as pd
import plotly.express as px
from google import genai

# ==================================================
# 1. PAGE CONFIGURATION
# ==================================================

st.set_page_config(
    page_title="Performance Drop Alert",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================================================
# 2. PROFESSIONAL DESIGN
# ==================================================

st.markdown("""
<style>
.stApp {
    background-color: #f3f6fc;
}
[data-testid="stSidebar"] {
    background-color: #12345a;
}
[data-testid="stSidebar"] * {
    color: white !important;
}
h1, h2, h3 {
    color: #174a7e;
}
div[data-testid="stMetric"] {
    background: white;
    border: 1px solid #dce5f0;
    padding: 17px;
    border-radius: 12px;
    box-shadow: 0 2px 7px rgba(0,0,0,0.05);
}
.stButton button {
    background-color: #1769aa;
    color: white;
    border-radius: 8px;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

# ==================================================
# 3. HEADER AND NAVIGATION
# ==================================================

st.title("📊 Performance Drop Alert")
st.caption("Student Performance Monitoring and Early Warning System")

st.sidebar.title("🎓 Student Monitor")
st.sidebar.caption("Academic Performance System")

page = st.sidebar.radio(
    "MAIN MENU",
    ["Dashboard", "Add Student", "Student Records", "About Project"]
)

# ==================================================
# 4. STUDENT DATABASE
# ==================================================

COLUMNS = [
    "Roll",
    "Name",
    "Student Email",
    "Attendance %",
    "Internal Marks",
    "Previous Semester %",
    "Risk Level",
    "Reason",
    "Gemini AI Analysis"
]

def get_risk_and_reason(attendance, internal):
    """Apply the exact risk rules from the project instructions."""
    if attendance < 60 and internal < 40:
        return (
            "High Risk",
            "Attendance is below 60% and internal marks are below 40%."
        )
    elif attendance < 75 or internal < 50:
        return (
            "Medium Risk",
            "Attendance is below 75% or internal marks are below 50%."
        )
    else:
        return (
            "Low Risk",
            "Attendance and internal marks meet the stated risk criteria."
        )

if "students" not in st.session_state:
    demo_data = [
        [101, "Aman", "", 55, 35, 65],
        [102, "Simran", "", 68, 45, 72],
        [103, "Rohan", "", 85, 75, 80],
        [104, "Priya", "", 48, 30, 60],
        [105, "Rahul", "", 72, 55, 68],
        [106, "Neha", "", 92, 88, 85],
        [107, "Karan", "", 58, 50, 70],
        [108, "Anjali", "", 45, 35, 55],
        [109, "Arjun", "", 78, 42, 75],
        [110, "Meena", "", 88, 65, 82],
    ]

    initial_rows = []
    for roll, name, email, attendance, internal, previous in demo_data:
        risk, reason = get_risk_and_reason(attendance, internal)
        initial_rows.append({
            "Roll": roll,
            "Name": name,
            "Student Email": email,
            "Attendance %": attendance,
            "Internal Marks": internal,
            "Previous Semester %": previous,
            "Risk Level": risk,
            "Reason": reason,
            "Gemini AI Analysis": (
                "Demo record. Use the Student Records page to view this "
                "record, or add a new student to generate a Gemini report."
            )
        })

    st.session_state.students = pd.DataFrame(initial_rows, columns=COLUMNS)

# Keep the app compatible with an existing session created by an older version.
for column in COLUMNS:
    if column not in st.session_state.students.columns:
        st.session_state.students[column] = ""

st.session_state.students = st.session_state.students[COLUMNS]

# Track successful automatic/manual email sends for this app session.
if "sent_alerts" not in st.session_state:
    st.session_state.sent_alerts = set()

# ==================================================
# 5. GEMINI AI ANALYSIS
# ==================================================

def analyse_student(attendance, internal, previous):
    risk, reason = get_risk_and_reason(attendance, internal)

    try:
        api_key = st.secrets["gemini"]["api_key"]
        client = genai.Client(api_key=api_key)

        prompt = f"""
You are an academic performance assistant.

Analyse the following student data:

Attendance: {attendance}%
Internal Marks: {internal}%
Previous Semester Percentage: {previous}%
Rule-based Risk Level: {risk}
Rule-based Reason: {reason}

Prepare a report in simple English with these headings:

1. Academic Performance Analysis
2. Gemini AI Assessment
3. Reasons for Concern
4. Personalised Improvement Plan
Give four practical suggestions.
5. Mentor Recommendation

Important:
- Do not change the given rule-based risk level.
- Do not claim certainty or invent future marks.
- Base your analysis only on the supplied information.
"""

        # Try the main Gemini model first, then a lighter fallback model
        # if Google reports temporary overload / service unavailability.
        models_to_try = ["gemini-3.8-flash", "gemini-3.5-flash-lite"]
        last_error = None

        for model_name in models_to_try:
            for attempt in range(2):
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt
                    )
                    if response.text:
                        return risk, response.text
                    last_error = RuntimeError(
                        f"{model_name} returned an empty response."
                    )
                    break
                except Exception as error:
                    last_error = error
                    error_text = str(error).lower()
                    temporary_error = (
                        "503" in error_text
                        or "unavailable" in error_text
                        or "overloaded" in error_text
                    )
                    if temporary_error and attempt == 0:
                        time.sleep(2)
                        continue
                    # Try the fallback model for temporary capacity errors.
                    if temporary_error:
                        break
                    # For authentication, permission, or other errors,
                    # stop rather than masking the real configuration issue.
                    raise

        raise RuntimeError(
            "Gemini models are temporarily unavailable. "
            "Please try again later. Last error: "
            f"{last_error}"
        )

    except Exception as error:
        return risk, (
            "Gemini AI analysis is temporarily unavailable. "
            "The rule-based risk result is still available. "
            f"Technical detail: {error}"
        )

# ==================================================
# 6. EMAIL ALERT FUNCTION
# ==================================================


def send_alert(name, receiver, reason, risk):
    """Send an alert using Gmail SMTP and Streamlit Secrets."""

    try:
        sender = st.secrets["email"]["sender_email"]
        password = st.secrets["email"]["app_password"]
        recipient = st.secrets["email"]["recipient_email"]

        if not recipient or not re.match(
            r"^[^@\s]+@[^@\s]+\.[^@\s]+$", recipient
        ):
            return False, "Please add a valid recipient_email in Secrets."

        message = EmailMessage()
        message["Subject"] = "Student Performance Alert - High Risk"
        message["From"] = sender
        message["To"] = recipient

        message.set_content(
            f"Dear Mentor,\n\n"
            f"Student Name: {name}\n"
            f"Risk Level: {risk}\n"
            f"Reason: {reason}\n\n"
            "Please review this student's academic performance "
            "and provide appropriate support.\n\n"
            "Regards,\nPerformance Drop Alert System"
        )

        with smtplib.SMTP_SSL(
            "smtp.gmail.com", 465, timeout=20
        ) as smtp:
            smtp.login(sender, password)
            smtp.send_message(message)

        return True, "Email alert sent successfully to the mentor."

    except KeyError as error:
        return False, f"Missing email setting in Secrets: {error}"

    except Exception as error:
        return False, f"Email sending failed: {error}"
        

# ==================================================
# 7. DASHBOARD
# ==================================================

if page == "Dashboard":

    st.header("📈 Dashboard Overview")

    df = st.session_state.students.copy()

    total = len(df)
    high = len(df[df["Risk Level"] == "High Risk"])
    medium = len(df[df["Risk Level"] == "Medium Risk"])
    low = len(df[df["Risk Level"] == "Low Risk"])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Students", total)
    c2.metric("🔴 High Risk", high)
    c3.metric("🟠 Medium Risk", medium)
    c4.metric("🟢 Low Risk", low)

    st.divider()
    st.subheader("Student Risk Analysis")

    chart_data = pd.DataFrame({
        "Risk Level": ["High Risk", "Medium Risk", "Low Risk"],
        "Students": [high, medium, low]
    })

    left, right = st.columns(2)

    with left:
        st.markdown("**Bar Chart – Risk Distribution**")
        bar_fig = px.bar(
            chart_data,
            x="Risk Level",
            y="Students",
            color="Risk Level",
            text="Students",
            color_discrete_map={
                "High Risk": "#e74c3c",
                "Medium Risk": "#f39c12",
                "Low Risk": "#27ae60"
            }
        )
        bar_fig.update_layout(
            plot_bgcolor="white",
            paper_bgcolor="white",
            showlegend=False
        )
        st.plotly_chart(bar_fig, use_container_width=True)

    with right:
        st.markdown("**Pie Chart – Risk Percentage**")
        pie_fig = px.pie(
            chart_data,
            names="Risk Level",
            values="Students",
            hole=0.4,
            color="Risk Level",
            color_discrete_map={
                "High Risk": "#e74c3c",
                "Medium Risk": "#f39c12",
                "Low Risk": "#27ae60"
            }
        )
        st.plotly_chart(pie_fig, use_container_width=True)

    st.divider()
    st.subheader("Student Overview")
    st.dataframe(df, use_container_width=True, hide_index=True)

    if high > 0:
        st.warning(f"{high} student(s) require immediate attention.")
    else:
        st.success("No High Risk students at present.")

# ==================================================
# 8. ADD STUDENT
# ==================================================

elif page == "Add Student":

    st.header("➕ Add New Student")
    st.write("Enter academic details to analyse student performance.")

    with st.form("student_form"):
        left, right = st.columns(2)

        with left:
            roll = st.number_input("Roll Number", min_value=1, step=1)
            name = st.text_input("Student Name")
            student_email = st.text_input(
                "Student Email (required for email alert)",
                placeholder="student@example.com"
            )
            attendance = st.number_input(
                "Attendance (%)",
                min_value=0.0,
                max_value=100.0,
                value=75.0
            )

        with right:
            internal = st.number_input(
                "Internal Marks",
                min_value=0.0,
                max_value=100.0,
                value=50.0
            )
            previous = st.number_input(
                "Previous Semester (%)",
                min_value=0.0,
                max_value=100.0,
                value=70.0
            )

        submitted = st.form_submit_button(
            "Analyse Student",
            use_container_width=True
        )

    if submitted:
        if not name.strip():
            st.warning("Please enter the student name.")
        elif roll in st.session_state.students["Roll"].values:
            st.warning("This roll number already exists.")
        elif student_email.strip() and not re.match(
            r"^[^@\s]+@[^@\s]+\.[^@\s]+$", student_email.strip()
        ):
            st.warning("Please enter a valid email address, or leave it blank.")
        else:
            with st.spinner("Analysing student performance..."):
                risk, ai_analysis = analyse_student(
                    attendance,
                    internal,
                    previous
                )

            _, reason = get_risk_and_reason(attendance, internal)

            new_student = pd.DataFrame([{
                "Roll": int(roll),
                "Name": name.strip(),
                "Student Email": student_email.strip(),
                "Attendance %": attendance,
                "Internal Marks": internal,
                "Previous Semester %": previous,
                "Risk Level": risk,
                "Reason": reason,
                "Gemini AI Analysis": ai_analysis
            }])

            st.session_state.students = pd.concat(
                [st.session_state.students, new_student],
                ignore_index=True
            )

            st.success("Student added successfully!")
            st.subheader("Risk Analysis Result")
            st.write("**Risk Level:**", risk)
            st.write("**Reason:**", reason)

            st.subheader("🤖 Gemini AI Assessment")
            st.markdown(ai_analysis)

            # Automatically email newly added High Risk students if an
            # address and Gmail Secrets are configured.
            if risk == "High Risk":
                st.warning(
                    "This student requires immediate mentor attention."
                )
                if student_email.strip():
                    alert_key = f"{int(roll)}:{student_email.strip().lower()}"
                    if alert_key not in st.session_state.sent_alerts:
                        with st.spinner("Sending High Risk email alert..."):
                            sent, message = send_alert(
                                name.strip(),
                                student_email.strip(),
                                reason,
                                risk
                            )
                        if sent:
                            st.session_state.sent_alerts.add(alert_key)
                            st.success(message)
                        else:
                            st.warning(message)
                else:
                    st.info(
                        "No student email was entered. Add an email address "
                        "in the student record before sending an alert."
                    )

# ==================================================
# 9. STUDENT RECORDS
# ==================================================

elif page == "Student Records":

    st.header("📋 Student Records")
    df = st.session_state.students.copy()

    search = st.text_input("Search by student name or roll number")
    risk_filter = st.selectbox(
        "Filter by Risk Level",
        ["All", "High Risk", "Medium Risk", "Low Risk"]
    )

    if search:
        df = df[
            df["Name"].str.contains(search, case=False, na=False)
            | df["Roll"].astype(str).str.contains(search, na=False)
        ]

    if risk_filter != "All":
        df = df[df["Risk Level"] == risk_filter]

    st.dataframe(df, use_container_width=True, hide_index=True)

    st.subheader("🤖 View Gemini AI Report")
    records = st.session_state.students

    if not records.empty:
        selected_roll = st.selectbox(
            "Select Student Roll Number",
            records["Roll"].tolist(),
            key="report_roll"
        )
        selected = records[records["Roll"] == selected_roll].iloc[0]
        st.write("**Student:**", selected["Name"])
        st.write("**Risk Level:**", selected["Risk Level"])
        st.markdown(selected["Gemini AI Analysis"])

    # Manual resend option retained for records that need an alert.
    st.divider()
    st.subheader("📧 High Risk Email Alert")

    high_students = records[records["Risk Level"] == "High Risk"]

    if not high_students.empty:
        selected_email_roll = st.selectbox(
            "Select High Risk Student",
            high_students["Roll"].tolist(),
            key="email_roll"
        )
        email_student = high_students[
            high_students["Roll"] == selected_email_roll
        ].iloc[0]

        st.write("**Student:**", email_student["Name"])
        st.write("**Email:**", email_student["Student Email"] or "Not entered")

        if st.button("Send / Resend Email Alert"):
            alert_key = (
                f"{int(email_student['Roll'])}:"
                f"{str(email_student['Student Email']).strip().lower()}"
            )
            sent, message = send_alert(
                email_student["Name"],
                email_student["Student Email"],
                email_student["Reason"],
                email_student["Risk Level"]
            )
            if sent:
                st.session_state.sent_alerts.add(alert_key)
                st.success(message)
            else:
                st.error(message)
    else:
        st.info("No High Risk students found.")

    csv = records.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Download Student Records",
        data=csv,
        file_name="student_records.csv",
        mime="text/csv"
    )

# ==================================================
# 10. ABOUT PROJECT
# ==================================================

elif page == "About Project":

    st.header("ℹ️ About Performance Drop Alert")

    st.write("""
    Performance Drop Alert is a student academic monitoring
    system designed to identify students who may need
    additional academic support.

    ### Main Features

    - Student information management
    - Attendance and internal marks analysis
    - Rule-based risk classification
    - Gemini AI academic assessment
    - Personalised improvement recommendations
    - High Risk email notifications
    - Dashboard with bar and pie charts
    - Student search and filtering
    - CSV report download

    ### Risk Classification Rules

    **High Risk:** Attendance below 60% AND internal marks below 40%.

    **Medium Risk:** Attendance below 75% OR internal marks below 50%,
    unless the student is already High Risk.

    **Low Risk:** All other cases.

    ### Technologies Used

    - Python
    - Streamlit
    - Pandas
    - Plotly
    - Google Gemini API
    - Gmail SMTP
    """)

# ==================================================
# 11. SIDEBAR FOOTER
# ==================================================

st.sidebar.markdown("---")
st.sidebar.caption("BCA Internship Project")
st.sidebar.caption("Performance Drop Alert")
