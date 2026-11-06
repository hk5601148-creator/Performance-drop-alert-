
import re
import time
import smtplib
from pathlib import Path
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
# 4. PERMANENT CSV STUDENT DATABASE
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

# CSV file will be created in the same folder as app.py.
CSV_FILE = Path(__file__).parent / "students.csv"


def get_risk_and_reason(attendance, internal):
    """Apply the exact project risk classification rules."""

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


def save_students(df):
    """Save student records permanently in CSV format."""

    df = df[COLUMNS].copy()

    temp_file = CSV_FILE.with_suffix(".tmp")

    df.to_csv(temp_file, index=False, encoding="utf-8-sig")

    # Replace the old file only after successful saving.
    temp_file.replace(CSV_FILE)


def load_students():
    """Load existing CSV records or create initial demo records."""

    if CSV_FILE.exists():

        try:
            df = pd.read_csv(CSV_FILE)

            # Support older CSV files with missing columns.
            for column in COLUMNS:
                if column not in df.columns:
                    df[column] = ""

            df = df[COLUMNS]

            # Validate roll numbers.
            df["Roll"] = pd.to_numeric(
                df["Roll"], errors="coerce"
            )

            df = df.dropna(subset=["Roll"])
            df["Roll"] = df["Roll"].astype(int)

            return df.reset_index(drop=True)

        except Exception as error:
            st.error(
                f"Unable to read students.csv: {error}. "
                "Your existing file has not been overwritten."
            )
            st.stop()

    # Initial demo records.
    # These are created only when students.csv does not exist.

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

        risk, reason = get_risk_and_reason(
            attendance,
            internal
        )

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
                "Demo record. Use the Student Records page "
                "to view this record, or add a new student "
                "to generate a Gemini report."
            )
        })

    df = pd.DataFrame(initial_rows, columns=COLUMNS)

    save_students(df)

    return df


# Load records once per Streamlit session.

if "students" not in st.session_state:
    st.session_state.students = load_students()

# Ensure all required columns exist.

for column in COLUMNS:
    if column not in st.session_state.students.columns:
        st.session_state.students[column] = ""

st.session_state.students = (
    st.session_state.students[COLUMNS]
)

# Track successful email alerts during the current session.

if "sent_alerts" not in st.session_state:
    st.session_state.sent_alerts = set()


# ==================================================
# 5. GEMINI AI ANALYSIS
# ==================================================

def analyse_student(attendance, internal, previous):

    risk, reason = get_risk_and_reason(
        attendance,
        internal
    )

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

        # Retry temporary service-capacity errors once.

        for attempt in range(2):

            try:
                response = client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=prompt
                )

                if response.text:
                    return risk, response.text

                return risk, "Gemini returned an empty response."

            except Exception as error:

                error_text = str(error).lower()

                temporary_error = (
                    "503" in error_text
                    or "unavailable" in error_text
                    or "overloaded" in error_text
                )

                if temporary_error and attempt == 0:
                    time.sleep(2)
                    continue

                raise

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

    """Send an email using Gmail SMTP and Streamlit Secrets."""

    if not receiver or not re.match(
        r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
        receiver
    ):
        return False, "A valid student email address is required."

    try:

        sender = st.secrets["email"]["sender_email"]
        password = st.secrets["email"]["app_password"]

        message = EmailMessage()

        message["Subject"] = (
            "Student Performance Alert - High Risk"
        )

        message["From"] = sender
        message["To"] = receiver

        message.set_content(
            f"Dear {name},\n\n"
            f"Your academic performance has been classified as {risk}.\n\n"
            f"Reason: {reason}\n\n"
            "Recommended actions:\n"
            "1. Meet your academic mentor.\n"
            "2. Work on improving attendance.\n"
            "3. Prepare regularly for internal assessments.\n"
            "4. Follow a study plan with your mentor.\n\n"
            "Please contact your teacher or mentor for support.\n\n"
            "Regards,\n"
            "Performance Drop Alert System"
        )

        with smtplib.SMTP_SSL(
            "smtp.gmail.com",
            465,
            timeout=20
        ) as smtp:

            smtp.login(sender, password)
            smtp.send_message(message)

        return True, "Email alert sent successfully."

    except KeyError:

        return False, (
            "Email settings are not configured in Streamlit Secrets. "
            "Add sender_email and app_password under the email section."
        )

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
        "Risk Level": [
            "High Risk",
            "Medium Risk",
            "Low Risk"
        ],
        "Students": [
            high,
            medium,
            low
        ]
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

        st.plotly_chart(
            bar_fig,
            use_container_width=True
        )

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

        st.plotly_chart(
            pie_fig,
            use_container_width=True
        )

    st.divider()

    st.subheader("Student Overview")

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )

    if high > 0:

        st.warning(
            f"{high} student(s) require immediate attention."
        )

    else:

        st.success(
            "No High Risk students at present."
        )


# ==================================================
# 8. ADD STUDENT
# ==================================================

elif page == "Add Student":

    st.header("➕ Add New Student")

    st.write(
        "Enter academic details to analyse student performance."
    )

    with st.form("student_form"):

        left, right = st.columns(2)

        with left:

            roll = st.number_input(
                "Roll Number",
                min_value=1,
                step=1
            )

            name = st.text_input(
                "Student Name"
            )

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
            r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
            student_email.strip()
        ):

            st.warning(
                "Please enter a valid email address, or leave it blank."
            )

        else:

            with st.spinner(
                "Analysing student performance..."
            ):

                risk, ai_analysis = analyse_student(
                    attendance,
                    internal,
                    previous
                )

            _, reason = get_risk_and_reason(
                attendance,
                internal
            )

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

            # Add record to session and permanent CSV file.

            st.session_state.students = pd.concat(
                [
                    st.session_state.students,
                    new_student
                ],
                ignore_index=True
            )

            save_students(
                st.session_state.students
            )

            st.success(
                "Student added and saved successfully!"
            )

            st.subheader("Risk Analysis Result")

            st.write("**Risk Level:**", risk)
            st.write("**Reason:**", reason)

            st.subheader("🤖 Gemini AI Assessment")

            st.markdown(ai_analysis)

            # Automatic High Risk email alert.

            if risk == "High Risk":

                st.warning(
                    "This student requires immediate mentor attention."
                )

                if student_email.strip():

                    alert_key = (
                        f"{int(roll)}:"
                        f"{student_email.strip().lower()}"
                    )

                    if alert_key not in st.session_state.sent_alerts:

                        with st.spinner(
                            "Sending High Risk email alert..."
                        ):

                            sent, message = send_alert(
                                name.strip(),
                                student_email.strip(),
                                reason,
                                risk
                            )

                        if sent:

                            st.session_state.sent_alerts.add(
                                alert_key
                            )

                            st.success(message)

                        else:

                            st.warning(message)

                else:

                    st.info(
                        "No student email was entered. "
                        "Add an email address in the student record "
                        "before sending an alert."
                    )


# ==================================================
# 9. STUDENT RECORDS
# ==================================================

elif page == "Student Records":

    st.header("📋 Student Records")

    df = st.session_state.students.copy()

    search = st.text_input(
        "Search by student name or roll number"
    )

    risk_filter = st.selectbox(
        "Filter by Risk Level",
        [
            "All",
            "High Risk",
            "Medium Risk",
            "Low Risk"
        ]
    )

    if search:

        df = df[
            df["Name"].astype(str).str.contains(
                search,
                case=False,
                na=False
            )
            |
            df["Roll"].astype(str).str.contains(
                search,
                na=False
            )
        ]

    if risk_filter != "All":

        df = df[
            df["Risk Level"] == risk_filter
        ]

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )

    # --------------------------------------------------
    # EDIT AND DELETE STUDENT RECORDS
    # --------------------------------------------------

    st.divider()

    st.subheader("✏️ Manage Student Records")

    records = st.session_state.students.copy()

    if not records.empty:

        selected_roll = st.selectbox(
            "Select Student Roll Number",
            records["Roll"].tolist(),
            key="manage_roll"
        )

        selected_index = records.index[
            records["Roll"] == selected_roll
        ][0]

        selected_student = records.loc[
            selected_index
        ]

        st.write(
            "**Selected Student:**",
            selected_student["Name"]
        )

        # EDIT STUDENT

        with st.expander("✏️ Edit Student Details"):

            with st.form("edit_student_form"):

                edit_name = st.text_input(
                    "Student Name",
                    value=str(selected_student["Name"])
                )

                edit_email = st.text_input(
                    "Student Email",
                    value=str(selected_student["Student Email"])
                )

                edit_attendance = st.number_input(
                    "Attendance (%)",
                    min_value=0.0,
                    max_value=100.0,
                    value=float(selected_student["Attendance %"])
                )

                edit_internal = st.number_input(
                    "Internal Marks",
                    min_value=0.0,
                    max_value=100.0,
                    value=float(selected_student["Internal Marks"])
                )

                edit_previous = st.number_input(
                    "Previous Semester (%)",
                    min_value=0.0,
                    max_value=100.0,
                    value=float(selected_student["Previous Semester %"])
                )

                update_button = st.form_submit_button(
                    "Update Student Record"
                )

        
