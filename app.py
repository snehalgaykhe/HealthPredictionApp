
import os
import re
import sqlite3
from datetime import date, datetime

import pandas as pd
import streamlit as st
from google import genai


# --------------------------------------------------
# APPLICATION CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Health Prediction Application",
    page_icon="🩺",
    layout="wide",
)

DB_NAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), "health_records.db")


# --------------------------------------------------
# DATABASE FUNCTIONS
# --------------------------------------------------

def get_connection():
    conn = sqlite3.connect(DB_NAME, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database():
    """Create the patient table if it does not already exist."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                dob TEXT NOT NULL,
                email TEXT NOT NULL,
                glucose REAL NOT NULL,
                haemoglobin REAL NOT NULL,
                cholesterol REAL NOT NULL,
                remarks TEXT NOT NULL
            )
        """)


def list_patients():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM patients ORDER BY id DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def get_patient(patient_id):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM patients WHERE id = ?",
            (patient_id,),
        ).fetchone()
    return dict(row) if row else None


def insert_patient(full_name, dob, email, glucose,
                   haemoglobin, cholesterol, remarks):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO patients
            (full_name, dob, email, glucose, haemoglobin,
             cholesterol, remarks)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            full_name, dob, email, glucose,
            haemoglobin, cholesterol, remarks
        ))


def update_patient(patient_id, full_name, dob, email,
                   glucose, haemoglobin, cholesterol, remarks):
    with get_connection() as conn:
        cursor = conn.execute("""
            UPDATE patients
            SET full_name = ?, dob = ?, email = ?,
                glucose = ?, haemoglobin = ?,
                cholesterol = ?, remarks = ?
            WHERE id = ?
        """, (
            full_name, dob, email, glucose,
            haemoglobin, cholesterol, remarks, patient_id
        ))
        return cursor.rowcount > 0


def delete_patient(patient_id):
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM patients WHERE id = ?",
            (patient_id,),
        )
        return cursor.rowcount > 0


# --------------------------------------------------
# VALIDATION FUNCTIONS
# --------------------------------------------------

def validate_patient(full_name, dob, email,
                     glucose, haemoglobin, cholesterol):
    errors = []

    if not full_name or not full_name.strip():
        errors.append("Full Name is required.")
    elif len(full_name.strip()) > 100:
        errors.append("Full Name must be 100 characters or fewer.")

    try:
        parsed_dob = datetime.strptime(dob.strip(), "%d/%m/%Y").date()

        if parsed_dob > date.today():
            errors.append("Date of Birth cannot be in the future.")

    except (ValueError, AttributeError):
        errors.append(
            "Date of Birth must be a valid date in dd/mm/yyyy format."
        )

    if not email or not re.fullmatch(
        r"[^@\s]+@[^@\s]+\.[^@\s]+", email.strip()
    ):
        errors.append("Please enter a valid email address.")

    numeric_values = [
        ("Glucose", glucose),
        ("Haemoglobin", haemoglobin),
        ("Cholesterol", cholesterol),
    ]

    for label, value in numeric_values:
        try:
            number = float(value)

            if not 0 < number <= 100000:
                errors.append(
                    f"{label} must be greater than 0 and within a valid numeric range."
                )
        except (ValueError, TypeError):
            errors.append(f"{label} must be a valid number.")

    return errors


def show_errors(errors):
    for error in errors:
        st.error(error)


def format_dob(dob):
    """Display dates as dd/mm/yyyy where possible."""
    if not dob:
        return ""

    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(dob, fmt).strftime("%d/%m/%Y")
        except ValueError:
            continue

    return dob


# --------------------------------------------------
# GEMINI AI INTEGRATION
# --------------------------------------------------

def generate_health_remarks(glucose, haemoglobin, cholesterol):
    """Generate educational remarks using Gemini 3.6 Flash."""

    api_key = None

    try:
        api_key = st.secrets.get("GEMINI_API_KEY")
    except Exception:
        pass

    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "Gemini API key was not found. Check your secrets.toml file."
        )

    client = genai.Client(
        api_key=api_key,
        http_options={"timeout": 30000},
    )

    prompt = f"""
You are assisting with an educational health-record application.

Review the following laboratory values:
- Glucose: {glucose}
- Haemoglobin: {haemoglobin}
- Cholesterol: {cholesterol}

Write 3 to 5 concise sentences explaining what these measurements
may represent in general terms.

Important:
- The units and laboratory reference ranges have not been provided.
- Do not diagnose a disease or prescribe medication.
- Do not assume glucose fasting status.
- Explain that interpretation depends on units, reference ranges,
  age, medical history, and clinical context.
- Recommend discussing results with a qualified healthcare professional.
- Clearly describe this as educational information, not a diagnosis.
"""

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt,
    )

    remarks = (response.text or "").strip()

    if not remarks:
        raise RuntimeError("Gemini returned an empty response.")

    return remarks


# --------------------------------------------------
# HELPER: DATE INPUT
# --------------------------------------------------

def parse_date_for_widget(dob):
    """Convert a stored date to a date object for Streamlit."""
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(dob, fmt).date()
        except (ValueError, TypeError):
            continue

    return date(2000, 1, 1)


# --------------------------------------------------
# INITIALIZE APPLICATION
# --------------------------------------------------

initialize_database()

st.title("🩺 Health Prediction Application")
st.write(
    "Register, view, update, and manage patient health records "
    "with AI-generated educational remarks."
)

st.info(
    "Disclaimer: AI-generated remarks are for educational purposes "
    "only. They are not a medical diagnosis or a substitute for "
    "professional medical advice."
)

tab_add, tab_view, tab_update, tab_delete = st.tabs([
    "➕ Add Patient",
    "📋 View Patients",
    "✏️ Update Patient",
    "🗑️ Delete Patient",
])


# --------------------------------------------------
# ADD PATIENT
# --------------------------------------------------

with tab_add:
    st.subheader("Add New Patient")

    with st.form("add_patient_form", clear_on_submit=True):
        full_name = st.text_input("Full Name")

        dob = st.text_input(
            "Date of Birth (dd/mm/yyyy)",
            placeholder="28/04/1990",
        )

        email = st.text_input("Email Address")

        col1, col2, col3 = st.columns(3)

        with col1:
            glucose = st.number_input(
                "Glucose",
                min_value=0.0,
                value=0.0,
                step=1.0,
            )

        with col2:
            haemoglobin = st.number_input(
                "Haemoglobin",
                min_value=0.0,
                value=0.0,
                step=0.1,
            )

        with col3:
            cholesterol = st.number_input(
                "Cholesterol",
                min_value=0.0,
                value=0.0,
                step=1.0,
            )

        submitted = st.form_submit_button(
            "Generate AI Remarks & Save",
            use_container_width=True,
        )

    if submitted:
        errors = validate_patient(
            full_name, dob, email,
            glucose, haemoglobin, cholesterol,
        )

        if errors:
            show_errors(errors)
        else:
            with st.spinner("Generating educational health remarks..."):
                try:
                    remarks = generate_health_remarks(
                        glucose, haemoglobin, cholesterol
                    )

                    insert_patient(
                        full_name.strip(),
                        dob.strip(),
                        email.strip(),
                        glucose,
                        haemoglobin,
                        cholesterol,
                        remarks,
                    )

                    st.success("Patient record saved successfully.")
                    st.write("### AI-Generated Remarks")
                    st.write(remarks)

                except Exception as error:
                    st.error(
                        "Could not generate AI remarks or save the record."
                    )
                    st.caption(
                        f"Details: {type(error).__name__}: {error}"
                    )
                    st.info(
                        "No new record was saved by this submission. "
                        "Please try again later."
                    )


# --------------------------------------------------
# VIEW PATIENTS
# --------------------------------------------------

with tab_view:
    st.subheader("Patient Records")

    patients = list_patients()

    if patients:
        df = pd.DataFrame(patients)

        if "dob" in df.columns:
            df["dob"] = df["dob"].apply(format_dob)

        st.write(f"**Total records: {len(df)}**")

        search_text = st.text_input(
            "Search by name or email",
            key="view_search",
        )

        if search_text.strip():
            search_mask = (
                df["full_name"].astype(str).str.contains(
                    search_text, case=False, na=False
                )
                |
                df["email"].astype(str).str.contains(
                    search_text, case=False, na=False
                )
            )
            df = df[search_mask]

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
        )

        st.download_button(
            "Download displayed records as CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="patient_records.csv",
            mime="text/csv",
        )
    else:
        st.info("No patient records found. Add a patient to get started.")


# --------------------------------------------------
# UPDATE PATIENT
# --------------------------------------------------

with tab_update:
    st.subheader("Update Patient Record")

    patients = list_patients()

    if patients:
        patient_options = {
            f"ID {p['id']} - {p['full_name']} ({p['email']})": p["id"]
            for p in patients
        }

        selected_label = st.selectbox(
            "Select patient to update",
            list(patient_options.keys()),
            key="update_patient_selection",
        )

        selected_id = patient_options[selected_label]
        patient = get_patient(selected_id)

        if patient:
            with st.form("update_patient_form"):
                new_name = st.text_input(
                    "Full Name",
                    value=patient["full_name"],
                )

                new_dob = st.text_input(
                    "Date of Birth (dd/mm/yyyy)",
                    value=format_dob(patient["dob"]),
                )

                new_email = st.text_input(
                    "Email Address",
                    value=patient["email"],
                )

                col1, col2, col3 = st.columns(3)

                with col1:
                    new_glucose = st.number_input(
                        "Glucose",
                        min_value=0.0,
                        value=float(patient["glucose"]),
                        step=1.0,
                        key="update_glucose",
                    )

                with col2:
                    new_haemoglobin = st.number_input(
                        "Haemoglobin",
                        min_value=0.0,
                        value=float(patient["haemoglobin"]),
                        step=0.1,
                        key="update_haemoglobin",
                    )

                with col3:
                    new_cholesterol = st.number_input(
                        "Cholesterol",
                        min_value=0.0,
                        value=float(patient["cholesterol"]),
                        step=1.0,
                        key="update_cholesterol",
                    )

                regenerate = st.checkbox(
                    "Regenerate AI remarks using the updated values",
                    value=False,
                )

                new_remarks = st.text_area(
                    "Remarks",
                    value=patient["remarks"],
                    height=150,
                )

                update_submitted = st.form_submit_button(
                    "Update Patient",
                    use_container_width=True,
                )

            if update_submitted:
                errors = validate_patient(
                    new_name, new_dob, new_email,
                    new_glucose, new_haemoglobin, new_cholesterol,
                )

                if errors:
                    show_errors(errors)
                else:
                    try:
                        final_remarks = new_remarks.strip()

                        if regenerate:
                            with st.spinner("Regenerating AI remarks..."):
                                final_remarks = generate_health_remarks(
                                    new_glucose,
                                    new_haemoglobin,
                                    new_cholesterol,
                                )

                        if not final_remarks:
                            st.error("Remarks cannot be empty.")
                        else:
                            updated = update_patient(
                                selected_id,
                                new_name.strip(),
                                new_dob.strip(),
                                new_email.strip(),
                                new_glucose,
                                new_haemoglobin,
                                new_cholesterol,
                                final_remarks,
                            )

                            if updated:
                                st.success(
                                    f"Patient ID {selected_id} updated successfully."
                                )
                                st.rerun()
                            else:
                                st.error("No patient record was updated.")

                    except Exception as error:
                        st.error("Could not update the patient record.")
                        st.caption(
                            f"Details: {type(error).__name__}: {error}"
                        )
    else:
        st.info("There are no patient records to update.")


# --------------------------------------------------
# DELETE PATIENT
# --------------------------------------------------

with tab_delete:
    st.subheader("Delete Patient Record")

    patients = list_patients()

    if patients:
        delete_options = {
            f"ID {p['id']} - {p['full_name']} ({p['email']})": p["id"]
            for p in patients
        }

        delete_label = st.selectbox(
            "Select patient to delete",
            list(delete_options.keys()),
            key="delete_patient_selection",
        )

        delete_id = delete_options[delete_label]
        delete_patient_data = get_patient(delete_id)

        if delete_patient_data:
            st.warning(
                f"You selected patient ID {delete_id}: "
                f"{delete_patient_data['full_name']}."
            )

            confirm_delete = st.checkbox(
                "I confirm that I want to permanently delete this record.",
                key="confirm_delete",
            )

            if st.button(
                "Delete Patient",
                type="primary",
                disabled=not confirm_delete,
            ):
                deleted = delete_patient(delete_id)

                if deleted:
                    st.success(
                        f"Patient ID {delete_id} deleted successfully."
                    )
                    st.rerun()
                else:
                    st.error("The patient record could not be deleted.")
    else:
        st.info("There are no patient records to delete.")


# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.divider()
st.caption(
    "Health Prediction Application | SQLite database | "
    "Gemini AI-generated educational remarks"
)
