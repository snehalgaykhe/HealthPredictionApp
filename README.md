# Health Prediction Application

A Python-based health record management application built using Streamlit and SQLite, with Gemini AI integration for generating educational health remarks.

## Features
- Add, view, update, and delete patient records.
- Validate patient details, email addresses, dates of birth, and health measurements.
- Store patient data in an SQLite database.
- Generate educational health remarks using the Google Gemini API.
- Search and export patient records to CSV.

## Technologies Used
- Python
- Streamlit
- SQLite
- Google Gemini API
- Pandas

## Setup Instructions
1. Clone or download this repository.
2. Install the required dependencies:
   `pip install -r requirements.txt`
3. Configure your Gemini API key in `.streamlit/secrets.toml` or the `GEMINI_API_KEY` environment variable.
4. Run the application:
   `streamlit run app.py`

## Security
Never upload API keys, secrets files, or patient database files to GitHub.

## Disclaimer
AI-generated remarks are for educational purposes only and are not a medical diagnosis or a substitute for professional medical advice.
