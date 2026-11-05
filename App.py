
import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(
    page_title="Performance Drop Alert",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Student Performance Drop Alert System")
st.write("Monitor student performance and identify students who need support.")

FILE = "students.csv"

# Load existing records
if os.path.exists(FILE):
    df = pd.read_csv(FILE)
else:
    df = pd.DataFrame({
        "Roll Number": ["101", "102", "103", "104", "105"],
        "Student Name": ["Aman", "Simran", "Rahul", "Priya", "Karan"],
        "Attendance": [55, 85, 70, 92, 45],
        "Internal Marks": [30, 75, 45, 88, 25],
        "Previous Semester %": [48, 82, 60, 90, 42]
    })

# Add new columns if older records do not have them
for column in ["Roll Number", "Previous Semester %"]:
    if column not in df.columns:
        df[column] = ""

# Risk prediction and reason
def predict_risk(row):
    attendance = float(row["Attendance"])
    marks = float(row["Internal Marks"])

    if attendance < 60 and marks < 40:
        return pd.Series([
            "High",
            "Attendance is below 60% and internal marks are below 40."
        ])
    elif attendance < 75 or marks < 50:
        reasons = []
        if attendance < 75:
            reasons.append("Attendance is below 75%")
        if marks < 50:
            reasons.append("Internal marks are below 50")
        return pd.Series(["Medium", " and ".join(reasons) + "."])
    else:
        return pd.Series(["Low", "Attendance and internal marks are satisfactory."])

df[["Risk Level", "Risk Reason"]] = df.apply(predict_risk, axis=1)

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

# Risk chart
st.header("📈 Student Risk Analysis")

risk_count = (
    df["Risk Level"].value_counts()
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

# Risk list and reasons
st.header("🚨 Risk Alerts")

for _, student in df.iterrows():
    message = (
        f'{student["Student Name"]} — '
        f'{student["Risk Level"]} Risk: {student["Risk Reason"]}'
    )
    if student["Risk Level"] == "High":
        st.error(message)
    elif student["Risk Level"] == "Medium":
        st.warning(message)
    else:
        st.success(message)

# Add student
st.header("➕ Add New Student")

with st.form("student_form"):
    roll = st.text_input("Roll Number")
    name = st.text_input("Student Name")
    attendance = st.number_input(
        "Attendance (%)", min_value=0.0, max_value=100.0
    )
    marks = st.number_input(
        "Internal Marks", min_value=0.0, max_value=100.0
    )
    previous = st.number_input(
        "Previous Semester (%)", min_value=0.0, max_value=100.0
    )

    submitted = st.form_submit_button("Add Student")

    if submitted:
        if name.strip() and roll.strip():
            new_student = pd.DataFrame([{
                "Roll Number": roll,
                "Student Name": name,
                "Attendance": attendance,
                "Internal Marks": marks,
                "Previous Semester %": previous
            }])

            saved_data = pd.concat([
                df[[
                    "Roll Number", "Student Name",
                    "Attendance", "Internal Marks",
                    "Previous Semester %"
                ]],
                new_student
            ], ignore_index=True)

            saved_data.to_csv(FILE, index=False)
            st.success("Student added successfully!")
            st.rerun()
        else:
            st.error("Please enter both roll number and student name.")
