import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta

st.set_page_config(page_title="Clinical Workflow System", layout="wide")

FILE = "patients.csv"
AUDIT_FILE = "audit_log.csv"

stages = ["Referral", "Triage", "Treatment", "Follow-up", "Discharged"]
roles = ["Doctor", "Nurse", "Admin"]

# -------------------
# INIT STATE
# -------------------
if "patients" not in st.session_state:
    if os.path.exists(FILE):
        st.session_state.patients = pd.read_csv(FILE).to_dict("records")
    else:
        st.session_state.patients = []

if "audit_log" not in st.session_state:
    if os.path.exists(AUDIT_FILE):
        st.session_state.audit_log = pd.read_csv(AUDIT_FILE).to_dict("records")
    else:
        st.session_state.audit_log = []

if "notes" not in st.session_state:
    st.session_state.notes = {}

if "selected_patient" not in st.session_state:
    st.session_state.selected_patient = None

if "role" not in st.session_state:
    st.session_state.role = "Doctor"

# -------------------
# SAVE HELPERS
# -------------------
def save_patients():
    pd.DataFrame(st.session_state.patients).to_csv(FILE, index=False)

def save_audit():
    pd.DataFrame(st.session_state.audit_log).to_csv(AUDIT_FILE, index=False)

# -------------------
# STATUS (SLA)
# -------------------
def get_status(updated_str):
    try:
        updated = datetime.strptime(updated_str, "%Y-%m-%d %H:%M:%S")
    except:
        updated = datetime.now()

    diff = datetime.now() - updated

    if diff < timedelta(hours=24):
        return "🟢 On Track"
    elif diff < timedelta(hours=48):
        return "🟠 At Risk"
    else:
        return "🔴 Stuck"

# -------------------
# SIDEBAR (PRO UI)
# -------------------
st.sidebar.title("Clinical System")

page = st.sidebar.radio("Navigation", ["Dashboard", "Patients", "Audit Log"])

st.session_state.role = st.sidebar.selectbox("Role", roles)

st.sidebar.markdown("---")
st.sidebar.info(f"Logged in as: **{st.session_state.role}**")

# -------------------
# DASHBOARD (CLEAN UI)
# -------------------
if page == "Dashboard":

    st.title("📊 Operations Dashboard")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Stage Overview")

        counts = {s: 0 for s in stages}

        for p in st.session_state.patients:
            if p["stage"] in counts:
                counts[p["stage"]] += 1

        for s in stages:
            st.metric(s, counts[s])

    with col2:
        st.subheader("System Summary")
        st.metric("Total Patients", len(st.session_state.patients))
        st.metric("Active Notes Records", len(st.session_state.notes))

# -------------------
# PATIENTS PAGE
# -------------------
elif page == "Patients":

    st.title("👤 Patients")

    # -------------------
    # ADD PATIENT
    # -------------------
    st.subheader("Add Patient")

    name = st.text_input("Patient Name")
    stage = st.selectbox("Initial Stage", stages)

    if st.button("Admit Patient"):
        if name.strip():

            st.session_state.patients.append({
                "name": name,
                "stage": stage,
                "updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

            st.session_state.audit_log.append({
                "name": name,
                "from": "Admission",
                "to": stage,
                "role": st.session_state.role,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

            save_patients()
            save_audit()
            st.rerun()

    st.divider()

    # -------------------
    # SEARCH + FILTER
    # -------------------
    search = st.text_input("Search Patient")

    filter_stage = st.selectbox("Filter by Stage", ["All"] + stages)

    st.divider()

    # -------------------
    # PATIENT LIST (CLICKABLE)
    # -------------------
    for i, p in enumerate(st.session_state.patients):

        if search and search.lower() not in p["name"].lower():
            continue

        if filter_stage != "All" and p["stage"] != filter_stage:
            continue

        col1, col2, col3 = st.columns([4, 2, 2])

        if col1.button(p["name"], key=f"open_{i}"):
            st.session_state.selected_patient = i

        col2.write(p["stage"])
        col3.write(get_status(p["updated"]))

    st.divider()

    # -------------------
    # PATIENT PROFILE
    # -------------------
    if st.session_state.selected_patient is not None:

        p = st.session_state.patients[st.session_state.selected_patient]

        st.subheader(f"Patient Profile: {p['name']}")

        # Stage dropdown (UPDATED FEATURE)
        old_stage = p["stage"]
        new_stage = st.selectbox("Update Stage", stages, index=stages.index(old_stage))

        if new_stage != old_stage:
            st.session_state.patients[st.session_state.selected_patient]["stage"] = new_stage
            st.session_state.patients[st.session_state.selected_patient]["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            st.session_state.audit_log.append({
                "name": p["name"],
                "from": old_stage,
                "to": new_stage,
                "role": st.session_state.role,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

            save_patients()
            save_audit()
            st.rerun()

        # Discharge shortcut
        if p["stage"] != "Discharged":
            if st.button("Discharge Patient"):
                old = p["stage"]

                st.session_state.patients[st.session_state.selected_patient]["stage"] = "Discharged"
                st.session_state.patients[st.session_state.selected_patient]["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                st.session_state.audit_log.append({
                    "name": p["name"],
                    "from": old,
                    "to": "Discharged",
                    "role": st.session_state.role,
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })

                save_patients()
                save_audit()
                st.rerun()

        st.divider()

        # -------------------
        # NOTES (PERSISTENT GLOBAL STORAGE)
        # -------------------
        st.subheader("Clinical Notes")

        key = p["name"]

        if key not in st.session_state.notes:
            st.session_state.notes[key] = []

        note = st.text_area("Write note")

        if st.button("Save Note") and note.strip():

            st.session_state.notes[key].append({
                "note": note,
                "role": st.session_state.role,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

            st.rerun()

        for n in reversed(st.session_state.notes[key]):
            st.info(f"{n['time']} | {n['role']}: {n['note']}")

# -------------------
# AUDIT LOG PAGE (FIXED + VISIBLE)
# -------------------
elif page == "Audit Log":

    st.title("📜 Audit Log")

    if len(st.session_state.audit_log) == 0:
        st.info("No audit records yet")
    else:
        df = pd.DataFrame(st.session_state.audit_log)

        st.dataframe(df, use_container_width=True)

        st.download_button(
            "Download Audit Log",
            df.to_csv(index=False),
            "audit_log.csv",
            "text/csv"
        )