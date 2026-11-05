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
st.write("Monitor student attendance and marks to identify students who need support.")

# Load student data
if os.path.exists("students.csv"):
    df = pd.read_csv("students.csv")
else:
    df = pd.DataFrame({
        "Student Name": ["Aman", "Simran", "Rahul", "Priya", "Karan"],
        "Attendance": [55, 85, 70, 92, 45],
        "Internal Marks": [30, 75, 45, 88, 25]
    })

# Calculate risk
def calculate_risk(row):
    if row["Attendance"] < 60 and row["Internal Marks"] < 40:
        return "High"
    elif row["Attendance"] < 75 or row["Internal Marks"] < 50:
        return "Medium"
    else:
        return "Low"

df["Risk Level"] = df.apply(calculate_risk, axis=1)

# Dashboard
st.subheader("📌 Dashboard")

col1, col2, col3 = st.columns(3)

col1.metric("Total Students", len(df))
col2.metric("High Risk", len(df[df["Risk Level"] == "High"]))
col3.metric("Medium Risk", len(df[df["Risk Level"] == "Medium"]))

# Student records
st.subheader("👩‍🎓 Student Records")
st.dataframe(df, use_container_width=True)

# Chart
st.subheader("📈 Student Risk Analysis")

risk_count = df["Risk Level"].value_counts().reset_index()
risk_count.columns = ["Risk Level", "Students"]

fig = px.pie(
