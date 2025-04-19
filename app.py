import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import plotly.express as px
import os
import re
import hashlib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from base64 import b64encode

USER_DB_FILE = "users.csv"

# --- Password Hashing ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# --- Email Validation ---
def is_valid_email(email):
    pattern = r"^[^@\s]+@[^@\s]+\.[a-zA-Z0-9]+$"
    return re.match(pattern, email) is not None

# --- Save New User ---
def save_user(student_id, email, password):
    hashed = hash_password(password)
    df = pd.DataFrame([[student_id, email, hashed]], columns=["student_id", "email", "password"])
    if os.path.exists(USER_DB_FILE):
        df.to_csv(USER_DB_FILE, mode='a', index=False, header=False)
    else:
        df.to_csv(USER_DB_FILE, index=False)

# --- Authenticate User ---
def authenticate_user(student_id, password):
    if os.path.exists(USER_DB_FILE):
        users = pd.read_csv(USER_DB_FILE, dtype={"student_id": str})
        hashed_password = hash_password(password)
        return any((users["student_id"] == str(student_id)) & (users["password"] == hashed_password))
    return False

# --- Send Alert Email ---
def send_low_balance_email(student_id, recipient_email, balance):
    sender_email = "your_email@gmail.com"
    sender_password = "your_email_password"  # Replace with your app password or use environment variable

    subject = "⚠️ Low GritGrab Balance Alert"
    body = f"""
    Hello {student_id},

    This is a friendly reminder that your GritGrab Dining Dollars balance is critically low.

    💳 Current Balance: ${balance:.2f}

    Please consider topping up or budgeting accordingly.

    - GritGrab Bot
    """

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = recipient_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, message.as_string())
            print(" Email sent successfully")
    except Exception as e:
        print("Failed to send email:", e)

# --- Streamlit Page Config ---
st.set_page_config(page_title="GritGrab", layout="wide")

# --- Registration Page ---
def register():
    st.title("Register New Account")
    with st.form("register_form"):
        new_id = st.text_input("Student ID")
        new_email = st.text_input("Email")
        new_pwd = st.text_input("Password", type="password")
        confirm_pwd = st.text_input("Confirm Password", type="password")
        submitted = st.form_submit_button("Create Account")

    if submitted:
        if new_pwd != confirm_pwd:
            st.error("Passwords do not match!")
        elif not new_id or not new_email or not new_pwd:
            st.error("Please fill all fields")
        elif not is_valid_email(new_email):
            st.error("Please enter a valid email address")
        elif os.path.exists(USER_DB_FILE) and new_id in pd.read_csv(USER_DB_FILE)["student_id"].values:
            st.error("Student ID already exists")
        else:
            save_user(new_id, new_email, new_pwd)
            st.success(f"Account created successfully for {new_id}")
            st.toast(f"👋 Welcome, {new_id}!")
            st.session_state["page"] = "login"
            st.rerun()

# --- Login Page ---
def login():
    st.title("🔐Student Login")
    student_id = st.text_input("Student ID", key="login_id")
    password = st.text_input("Password", type="password", key="login_pwd")
    forgot_password = st.checkbox("Forgot Password?", key="forgot_checkbox")
    remember_me = st.checkbox("Remember Me", key="remember_checkbox")

    if forgot_password:
        st.text_input("Enter your registered email", key="recovery_email")
        st.button("Reset Password")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Login"):
            if student_id and password and authenticate_user(student_id, password):
                st.session_state["authenticated"] = True
                st.session_state["student_id"] = student_id
                if remember_me:
                    st.session_state["remember_me"] = True
                st.rerun()
            else:
                st.error("Invalid credentials. Please try again.")
    with col2:
        if st.button("New User?"):
            st.session_state["page"] = "register"
            st.rerun()

# --- Auth Session Management ---
if "page" not in st.session_state:
    st.session_state["page"] = "login"
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "remember_me" in st.session_state and st.session_state["remember_me"]:
    st.session_state["authenticated"] = True

if not st.session_state["authenticated"]:
    if st.session_state["page"] == "login":
        login()
    elif st.session_state["page"] == "register":
        register()
    st.stop()

# --- Utility ---
def add_random_time(date):
    return datetime.combine(date.date(), datetime.min.time()) + timedelta(
        hours=random.randint(8, 19), minutes=random.randint(0, 59), seconds=random.randint(0, 59))

# --- Load and Prep Data ---
df = pd.read_csv("transactions.csv")
df["Date"] = pd.to_datetime(df["Date"])
df["Date"] = df["Date"].apply(add_random_time)
df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")
initial_credit = 1000
df["CumulativeSpend"] = df["Amount"].cumsum()
df["Balance"] = initial_credit + df["CumulativeSpend"]

# --- Sidebar Filters ---
st.sidebar.header("🔍 Filter")
min_date, max_date = df["Date"].min().date(), df["Date"].max().date()
start_date = st.sidebar.date_input("Start Date", min_date)
end_date = st.sidebar.date_input("End Date", max_date)
all_vendors = sorted(df["Description"].dropna().unique())
selected_vendor = st.sidebar.selectbox("Dining Location", options=["All"] + all_vendors, index=0)

if selected_vendor == "All":
    filtered_df = df[(df["Date"].dt.date >= start_date) & (df["Date"].dt.date <= end_date)]
else:
    filtered_df = df[(df["Date"].dt.date >= start_date) & (df["Date"].dt.date <= end_date) & (df["Description"] == selected_vendor)]

# --- Logout ---
st.sidebar.markdown("---")
if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()

# --- Header ---
st.markdown(f"""
    <h1 style='text-align: center; color: #1f77b4;'>GritGrab Dining Dollars</h1>
    <h4 style='text-align: center; color: #aaa;'>Student ID: <span style='color: #fff; background-color:#444; padding: 4px 8px; border-radius: 6px;'>{st.session_state['student_id']}</span></h4>
    <hr style='margin-top: 10px; margin-bottom: 30px;'>
""", unsafe_allow_html=True)

# --- Metrics ---
current_balance = filtered_df["Balance"].iloc[-1] if not filtered_df.empty else initial_credit
avg_daily_spend = abs(filtered_df["Amount"].mean()) if not filtered_df.empty else 0
days_left = current_balance / avg_daily_spend if avg_daily_spend > 0 else float("inf")
predicted_date = datetime.today() + timedelta(days=days_left)

# --- Email Alert on Low Balance ---
user_data = pd.read_csv(USER_DB_FILE)
email_row = user_data[user_data["student_id"] == st.session_state["student_id"]]
user_email = email_row["email"].values[0] if not email_row.empty else None
if current_balance < 20 and not st.session_state.get("alert_sent"):
    if user_email:
        send_low_balance_email(st.session_state["student_id"], user_email, current_balance)
        st.session_state["alert_sent"] = True

# --- UI Metrics ---
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("**💳 Current Balance**")
    st.markdown(f"<h3 style='color:#00ffcc;'>${current_balance:.2f}</h3>", unsafe_allow_html=True)
with col2:
    st.markdown("**🗕️ Avg Daily Spend**")
    st.markdown(f"<h3 style='color:#ffd700;'>${avg_daily_spend:.2f}</h3>", unsafe_allow_html=True)
with col3:
    st.markdown("**⏳ Days Left**")
    st.markdown(f"<h3 style='color:#ff6347;'>{days_left:.1f} days</h3>", unsafe_allow_html=True)

if selected_vendor != "All":
    vendor_total = filtered_df["Amount"].sum()
    st.markdown(f"<h4 style='color:#66ffcc;'>💰 Total spent at <b>{selected_vendor}</b>: <span style='color:#ffdd00;'>${abs(vendor_total):.2f}</span></h4>", unsafe_allow_html=True)

if avg_daily_spend > 7:
    st.warning("⚠️ You're spending more than usual!")
if days_left < 7:
    st.error("You might run out of Dining Dollars in less than a week!")

# --- Tabs ---
tab1, tab2, tab3 = st.tabs(["📈 Charts", "📊 Data", "📥 Download"])

with tab1:
    st.subheader("📉 Balance Over Time (Clear View)")
    fig1 = px.line(filtered_df.sort_values("Date"), x="Date", y="Balance", title="Balance Over Time", markers=True)
    fig1.update_layout(template="plotly_dark", height=450)
    st.plotly_chart(fig1, use_container_width=True)

    st.subheader("📅 Daily Spend")
    daily = filtered_df.groupby(filtered_df["Date"].dt.date)["Amount"].sum().reset_index()
    daily.columns = ["Date", "Total_Spend"]
    fig2 = px.line(daily, x="Date", y="Total_Spend", title="Daily Spend", markers=True)
    fig2.update_layout(template='plotly_dark', height=400)
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("🗓️ Monthly Spend")
    filtered_df["Month"] = filtered_df["Date"].dt.to_period("M").apply(lambda r: r.start_time)
    monthly = filtered_df.groupby("Month")["Amount"].sum().reset_index()
    fig3 = px.line(monthly, x="Month", y="Amount", title="Monthly Spend", markers=True)
    fig3.update_layout(template='plotly_dark', height=400)
    st.plotly_chart(fig3, use_container_width=True)

    if selected_vendor == "All":
        st.subheader("🥧 Spend by Vendor (Pie)")
        vendor_spend = filtered_df.groupby("Description")["Amount"].sum().abs().reset_index()
        fig4 = px.pie(vendor_spend, names="Description", values="Amount", title="Spend by Vendor")
        fig4.update_layout(template='plotly_dark')
        st.plotly_chart(fig4, use_container_width=True)
    else:
        st.info("Pie chart is only available when all vendors are selected.")

with tab2:
    st.subheader(" Filtered Transaction History")
    st.dataframe(filtered_df, use_container_width=True)

    st.subheader("🏆 Top 3 Visited Locations")
    st.table(filtered_df["Description"].value_counts().head(3).reset_index().rename(columns={"index": "Location", "Description": "Visits"}))

with tab3:
    st.subheader("⬇ Export Filtered Transactions")
    csv = filtered_df.to_csv(index=False).encode("utf-8")
    st.download_button(label="📥 Download as CSV", data=csv, file_name="filtered_transactions.csv", mime="text/csv")
