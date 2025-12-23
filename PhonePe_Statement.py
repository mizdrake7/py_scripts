import os, re
import pandas as pd
from PyPDF2 import PdfReader
from datetime import datetime
from collections import Counter

# =======================
# AUTO-DETECT STATEMENT
# =======================
pdf_file = next((f for f in os.listdir() 
                 if f.startswith("PhonePe_Statement") and f.endswith(".pdf")), None)

if not pdf_file:
    print("❌ No PhonePe statement found")
    exit()

print(f"📄 Detected: {pdf_file}")

# =======================
# EXTRACT DATA
# =======================
reader = PdfReader(pdf_file)
rows = []

pattern = r"([A-Za-z]{3}\s+\d{2},\s+\d{4}).*?(Paid to|Received from).*?(DEBIT|CREDIT)\s+₹([\d,]+(?:\.\d+)?)"

for page in reader.pages:
    text = page.extract_text() or ""
    matches = re.findall(pattern, text, re.DOTALL)
    for d, merchant, t, amt in matches:
        rows.append([
            datetime.strptime(d, "%b %d, %Y"),
            merchant.strip(),
            t.strip(),
            float(amt.replace(",", ""))
        ])

df = pd.DataFrame(rows, columns=["Date", "Merchant", "Type", "Amount"])

# =======================
# CORE TOTALS
# =======================
total_spent = df[df.Type=="DEBIT"].Amount.sum()
total_received = df[df.Type=="CREDIT"].Amount.sum()
net = total_received - total_spent

# =======================
# ADVANCED OUTPUTS
# =======================
df["Month"] = df.Date.dt.to_period("M")
monthly = df.groupby(["Month","Type"]).Amount.sum().unstack().fillna(0)

daily = df.groupby("Date").Amount.sum()
top_expenses = df[df.Type=="DEBIT"].nlargest(10, "Amount")
top_merchants = Counter(df.Merchant).most_common(15)

big_spends = df[(df.Type=="DEBIT") & (df.Amount >= 500)]
small_spends = df[(df.Type=="DEBIT") & (df.Amount < 50)]

weekday_pattern = df.groupby(df.Date.dt.day_name()).Amount.sum()
hour_pattern = df.groupby(df.Date.dt.hour).Amount.sum()

# =======================
# EXPORT EVERYTHING
# =======================
with pd.ExcelWriter("PhonePe_Full_Report.xlsx") as writer:
    df.to_excel(writer, sheet_name="All_Transactions", index=False)
    monthly.to_excel(writer, sheet_name="Monthly_Summary")
    top_expenses.to_excel(writer, sheet_name="Top_Expenses", index=False)
    big_spends.to_excel(writer, sheet_name="Big_Expenses", index=False)
    small_spends.to_excel(writer, sheet_name="Small_Expenses", index=False)
    weekday_pattern.to_excel(writer, sheet_name="Weekday_Pattern")
    hour_pattern.to_excel(writer, sheet_name="Hour_Pattern")

# =======================
# DISPLAY SUMMARY
# =======================
print("\n========== FINAL SUMMARY ==========")
print(f"💸 Total Spent    : ₹{round(total_spent,2)}")
print(f"💰 Total Received: ₹{round(total_received,2)}")
print(f"📊 Net Balance   : ₹{round(net,2)}")
print(f"📁 Report saved: PhonePe_Full_Report.xlsx")

print("\n🔥 Top 10 Expenses")
print(top_expenses[['Date','Amount']])

print("\n🏪 Top Merchants")
for m,c in top_merchants[:10]:
    print(f"{m} — {c} transactions")
