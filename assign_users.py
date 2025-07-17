import pandas as pd
import toml
import random
from itertools import cycle

# --- Config ---
PARQUET_PATH = r'O:\Users\VictorM\Python Scripts\ARDS-QUEST VACXR Annotation Tool\VA_firstBatch.parquet'
SECRETS_PATH = r'O:\Users\VictorM\Python Scripts\ARDS-QUEST VACXR Annotation Tool\.streamlit\secrets.toml'
OUTPUT_PATH =  r'O:\Users\VictorM\Python Scripts\ARDS-QUEST VACXR Annotation Tool\VA_firstBatch_new.parquet'

# --- Load secrets ---
secrets = toml.load(SECRETS_PATH)
credentials = secrets["credentials"]

# Separate users by role
clinicians = [user for user, info in credentials.items() if info["role"] == "Clinician"]
ds_users = [user for user, info in credentials.items() if info["role"] == "DS"]

if not clinicians or not ds_users:
    raise ValueError("No clinicians or DS users found in secrets.")

# --- Load data ---
df = pd.read_parquet(PARQUET_PATH)

if "subject_icn" not in df.columns:
    raise ValueError("The DataFrame must contain a 'subject_icn' column.")

# --- Assign AssignedDS (random + even) ---
random.shuffle(ds_users)
ds_cycle = cycle(ds_users)
df["AssignedDS"] = [next(ds_cycle) for _ in range(len(df))]

# --- Assign AssignedClinician based on subject_icn ---
random.shuffle(clinicians)
unique_icns = df["subject_icn"].unique()
clinician_cycle = cycle(clinicians)
icn_to_clinician = {icn: next(clinician_cycle) for icn in unique_icns}
df["AssignedClinician"] = df["subject_icn"].map(icn_to_clinician)

# --- Save output ---
df.to_parquet(OUTPUT_PATH, index=False)
print(f"Updated DataFrame saved to: {OUTPUT_PATH}")
