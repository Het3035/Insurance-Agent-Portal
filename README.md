# Insurance Agent Portal

A Flask-based web application for insurance agents to issue policies, calculate quotes, manage policy details, renew coverage, and submit claims.

## Features
- **Authentication**: Secure agent login.
- **Quote Calculator**: Compares premium quotes across multiple providers (ICICI, New India, Tata AIG) based on member ages and Sum Insured.
- **Policy Management**: Easily issue, view, renew, and delete policies.
- **Claims Processing**: File claims against active policies, dynamically updating the remaining sum insured.
- **Reports Dashboard**: Aggregated stats on active/expired policies, total premium collected, and upcoming renewals.
- **Email Notifications**: Automatic email confirmation for policy issuance, renewal, and upcoming expiry alerts.

## Setup & Running

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment Variables**:
   Create a `.env` file in the root directory:
   ```env
   SECRET_KEY=your_secret_key
   EMAIL_USER=your_email@gmail.com
   EMAIL_PASS=your_app_password
   ```

3. **Seed Database Rates**:
   Populate the premium rate charts in the database:
   ```bash
   python seed_quotes.py
   ```

4. **Run the Application**:
   Start the development server:
   ```bash
   python app.py
   ```
   Open `http://127.0.0.1:5000` in your web browser.
