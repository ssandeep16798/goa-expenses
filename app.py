import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Goa Trip Splitter", layout="wide", page_icon="🏖️")

# --- ROBUST & CLEAN FANCY CSS ---
st.markdown("""
    <style>
    /* 1. Gradient Background (Sunset Vibe) */
    .stApp {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        color: white;
    }

    /* 2. Style the Containers */
    div[data-testid="column"] {
        background-color: rgba(255, 255, 255, 0.05);
        padding: 20px;
        border-radius: 15px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }

    /* 3. Global Text Color Fix */
    h1, h2, h3, label, p, span, .stMarkdown {
        color: #ffffff !important;
    }

    /* 4. Input Field Styling */
    input, select, textarea {
        background-color: #ffffff !important;
        color: #000000 !important;
    }

    /* 5. The "Sync" Button */
    div.stButton > button:first-child {
        background: #ff4b2b;
        background: -webkit-linear-gradient(to right, #ff416c, #ff4b2b);
        background: linear-gradient(to right, #ff416c, #ff4b2b);
        color: white;
        border: none;
        font-weight: bold;
        border-radius: 10px;
        padding: 15px;
        font-size: 18px;
    }

    /* 6. Metric Styling */
    [data-testid="stMetricValue"] {
        color: #fbff00 !important; /* Bright yellow for visibility */
    }
    </style>
    """, unsafe_allow_html=True)

# --- DB CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1N6WUMvWnOibUWoBZ8sxk38dJwJjn0hyEifKislOdrfU/edit#gid=0"
df = conn.read(spreadsheet=SHEET_URL, ttl="0s")
FRIENDS = ["Sandeep", "Mahyur", "Loknath"]

st.title("🏖️ Goa Trip Expense Splitter")
st.write("Fuck off BC!")

current_user = st.selectbox("Who are you?", FRIENDS)

# --- 1. TOP SUMMARY ---
if not df.empty:
    m = st.columns(len(FRIENDS) + 1)
    m[0].metric("Total Trip", f"₹{df['Amount'].sum():,.0f}")
    for i, friend in enumerate(FRIENDS):
        paid = df[df['Payer'] == friend]['Amount'].sum()
        m[i+1].metric(f"{friend} Paid", f"₹{paid:,.0f}")

st.divider()

# --- 2. INPUT SECTION ---
st.subheader("📝 Record an Expense")

# We use columns to keep things neat
c1, c2, c3 = st.columns([1, 2, 1])
with c1:
    date = st.date_input("Date", datetime.now())
with c2:
    reason = st.text_input("Reason", placeholder="e.g., Dinner at Thalassa")
with c3:
    amount = st.number_input("Amount (INR)", min_value=0.0, step=1.0, format="%.2f")

c4, c5 = st.columns(2)
with c4:
    payer = st.selectbox("Who paid?", FRIENDS)
with c5:
    mode = st.radio("How to split?", ["Equally", "Unequally"], horizontal=True)

shares = {f: 0.0 for f in FRIENDS}

if mode == "Equally":
    share_val = amount / len(FRIENDS)
    for f in FRIENDS: shares[f] = share_val
    st.info(f"💡 Splitting equally: ₹{share_val:,.2f} each.")
else:
    st.write("---")
    who_shares = st.multiselect("Who is involved?", FRIENDS, default=FRIENDS)
    
    if who_shares:
        num_people = len(who_shares)
        default_share = round(amount / num_people, 2) if amount > 0 else 0.0
        
        input_cols = st.columns(num_people)
        for i, friend in enumerate(who_shares):
            # The key fix we did earlier
            unique_key = f"share_{friend}_{num_people}"
            shares[friend] = input_cols[i].number_input(
                f"{friend}", min_value=0.0, value=default_share, 
                step=1.0, key=unique_key
            )
        
        if round(sum(shares.values()), 2) != round(amount, 2):
            st.warning("⚠️ Totals don't match the bill yet!")
        else:
            st.success("✅ Split is perfectly balanced.")

# --- 3. SAVE ---
if st.button("🚀 SYNC TO SHEET"):
    if amount <= 0:
        st.error("Enter a valid amount!")
    elif mode == "Unequally" and round(sum(shares.values()), 2) != round(amount, 2):
        st.error("Check the math—it doesn't match the total bill!")
    else:
        new_row = pd.DataFrame([{
            "Date": str(date), "Reason": reason, "Amount": amount,
            "Payer": payer, "Split_Mode": mode, **shares
        }])
        updated_df = pd.concat([df, new_row], ignore_index=True)
        conn.update(spreadsheet=SHEET_URL, data=updated_df)
        st.success("Synced to the cloud!")
        st.rerun()

# --- 4. HISTORY ---
if not df.empty:
    st.divider()
    st.subheader("📊 Recent Transactions")
    
    for index, row in df.iterrows():
        with st.container():
            cols = st.columns([2, 3, 2, 2, 1])
            cols[0].write(row['Date'])
            cols[1].write(row['Reason'])
            cols[2].write(f"₹{row['Amount']:.0f}")
            cols[3].write(row['Payer'])
            
            if row['Payer'] == current_user:
                if cols[4].button("🗑️", key=f"delete_{index}"):
                    # Confirm delete
                    if st.session_state.get(f"confirm_delete_{index}", False):
                        # Delete the row
                        updated_df = df.drop(index).reset_index(drop=True)
                        conn.update(spreadsheet=SHEET_URL, data=updated_df)
                        st.success("Expense deleted!")
                        st.rerun()
                    else:
                        st.session_state[f"confirm_delete_{index}"] = True
                        st.warning("Click again to confirm delete.")
            else:
                cols[4].write("")  # Empty for others