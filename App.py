
import streamlit as st
import pandas as pd
import plotly.express as px
import smtplib
from email.message import EmailMessage
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
    "Attendance %",
    "Internal Marks",
    "Previous Semester %",
    "Risk Level",
    "Reason",
    "Gemini AI Analysis"
]

if "students" not in st.session_state:
    st.session_state.students = pd.DataFrame([
        [
            101, "Aman", 55, 35, 65,
            "High Risk",
            "Low attendance and low internal marks.",
            "Demo analysis: performance needs immediate attention."
        ],
        [
            102, "Simran", 68, 45, 72,
            "Medium Risk",
            "Attendance or internal marks need improvement.",
            "Demo analysis: regular study and attendance are recommended."
        ],
        [
            103, "Rohan", 85, 75, 80,
            "Low Risk",
            "Student performance is satisfactory.",
            "Demo analysis: maintain current academic performance."
        ]
    ], columns=COLUMNS)

# ==================================================
# 5. RISK CLASSIFICATION AND GEMINI AI
# ==================================================

def analyse_student(attendance, internal, previous):

    # Exact project risk rules
    if attendance < 60 and internal < 40:
        risk = "High Risk"

    elif attendance < 75 or internal < 50:
        risk = "Medium Risk"

    else:
        risk = "Low Risk"

    # Gemini AI analysis
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

Prepare a report in simple English with these headings:

1. Academic Performance Analysis
Explain the student's current performance.

2. Gemini AI Assessment
Give a cautious assessment of possible future academic
performance. Do not claim certainty or invent future marks.

3. Reasons for Concern
Mention the important factors affecting performance.

4. Personalised Improvement Plan
Give four practical suggestions for improvement.

5. Mentor Recommendation
Explain what the teacher or mentor should do.

Important:
Do not change the given rule-based risk level.
Base your analysis only on the supplied information.
"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        if response.text:
            return risk, response.text

        return risk, "Gemini returned an empty response."

    except Exception as error:
        return risk, (
            "Gemini AI analysis could not be completed. "
            "Please check the API key and connection. "
            f"Technical detail: {error}"
        )

# ==================================================
# 6. EMAIL ALERT FUNCTION
# ==================================================

def send_alert(name, reason):

    try:
        sender = st.secrets["email"]["sender_email"]
        password = st.secrets["email"]["app_password"]
        receiver = st.secrets["email"]["recipient_email"]

        message = EmailMessage()
        message["Subject"] = "Student Performance Alert"
        message["From"] = sender
        message["To"] = receiver

        message.set_content(
            f"Dear {name},\n\n"
            f"You have been identified as a High Risk student.\n\n"
            f"Reason: {reason}\n\n"
            "Please meet your mentor and prepare an improvement plan.\n\n"
            "Regards,\nStudent Performance Monitoring System"
        )

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(sender, password)
            smtp.send_message(message)

        return True

    except Exception as error:
        st.error(f"Email sending failed: {error}")
        return False

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

    # Summary cards
    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Total Students", total)
    c2.metric("🔴 High Risk", high)
    c3.metric("🟠 Medium Risk", medium)
    c4.metric("🟢 Low Risk", low)

    st.divider()

    # Charts
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
            roll = st.number_input(
                "Roll Number",
                min_value=1,
                step=1
            )

            name = st.text_input("Student Name")

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

        else:
            with st.spinner("Analysing student with Gemini AI..."):

                risk, ai_analysis = analyse_student(
                    attendance,
                    internal,
                    previous
                )

            # Keep the fixed rule-based reason separate
            if attendance < 60 and internal < 40:
                reason = (
                    "Attendance is below 60% and "
                    "internal marks are below 40%."
                )
            elif attendance < 75 or internal < 50:
                reason = (
                    "Attendance is below 75% or "
                    "internal marks are below 50%."
                )
            else:
                reason = "Student performance meets the risk criteria."

            new_student = pd.DataFrame([{
                "Roll": int(roll),
                "Name": name.strip(),
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

            if risk == "High Risk":
                st.warning(
                    "This student requires immediate mentor attention."
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
        ["All", "High Risk", "Medium Risk", "Low Risk"]
    )

    if search:
        df = df[
            df["Name"].str.contains(
                search, case=False, na=False
            )
            |
            df["Roll"].astype(str).str.contains(
                search, na=False
            )
        ]

    if risk_filter != "All":
        df = df[df["Risk Level"] == risk_filter]

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )

    # View saved AI analysis
    st.subheader("🤖 View Gemini AI Report")

    records = st.session_state.students

    if not records.empty:

        selected_roll = st.selectbox(
            "Select Student Roll Number",
            records["Roll"].tolist(),
            key="report_roll"
        )

        selected = records[
            records["Roll"] == selected_roll
        ].iloc[0]

        st.write("**Student:**", selected["Name"])
        st.write("**Risk Level:**", selected["Risk Level"])
        st.markdown(selected["Gemini AI Analysis"])

    # Email alert
    st.divider()
    st.subheader("📧 High Risk Email Alert")

    high_students = records[
        records["Risk Level"] == "High Risk"
    ]

    if not high_students.empty:

        selected_email_roll = st.selectbox(
            "Select High Risk Student",
            high_students["Roll"].tolist(),
            key="email_roll"
        )

        email_student = high_students[
            high_students["Roll"] == selected_email_roll
        ].iloc[0]

        if st.button("Send Email Alert"):

            if send_alert(
                email_student["Name"],
                email_student["Reason"]
            ):
                st.success("Email alert sent successfully!")

    else:
        st.info("No High Risk students found.")

    # CSV download
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
