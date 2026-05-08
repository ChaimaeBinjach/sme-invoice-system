# SME Invoice System

A lightweight invoice management web application built with **Python**, **Flask**, **SQLite**, **SQLAlchemy**, **Jinja templates**, and **Bootstrap**.

This project was developed as a research prototype. It demonstrates how a small or medium-sized enterprise (SME) can manage customer records, create and monitor invoices, follow payment status, identify due-soon and overdue invoices, export invoice data, and reuse the same database for simple analytics.

The system is **not** a certified accounting product or legally approved invoicing system. It is a prototype for process analysis, implementation, testing, and evaluation.

---

## 1. Main features

- Customer management: create, edit, list, and deactivate customers.
- Invoice management: create, edit, view, and list invoices.
- Invoice line items: add up to three optional line items per invoice form.
- Status tracking: Draft, Sent, and Paid status values.
- Due-soon view: list unpaid invoices due within the next 7 days.
- Overdue view: list invoices that are not Paid and have a due date in the past.
- Dashboard: show total customers, total invoices, total invoiced amount, unpaid amount, overdue amount, and overdue invoice list.
- Settings page: configure default tax percentage and default currency.
- CSV export: export invoice data for spreadsheet use or accountant support.
- Offline analytics: run a console report from the same SQLite database.
- Demo data utilities: insert synthetic customer and invoice data for testing and screenshots.

---

## 2. Project structure

```text
SME_Invoice_System/
├── app.py                  # Main Flask application, database models, routes and business logic
├── analytics.py            # Offline analytics script using the same SQLite database
├── invoice.db              # SQLite demo database with synthetic sample data
├── requirements.txt        # Python dependencies
├── .gitignore              # Files/folders excluded from version control
├── static/
│   ├── favicon.png
│   └── style.css           # Small custom styling on top of Bootstrap
└── templates/
    ├── base.html           # Shared layout, navigation and footer
    ├── home.html
    ├── dashboard.html
    ├── invoices_list.html
    ├── invoice_form.html
    ├── invoice_detail.html
    ├── customers_list.html
    ├── customer_form.html
    └── settings.html
```

---

## 3. Requirements

Recommended environment:

- Python 3.11 or newer
- pip
- A web browser such as Chrome, Edge, or Firefox

Python packages are listed in `requirements.txt`:

```text
Flask==3.1.2
Flask-SQLAlchemy==3.1.1
SQLAlchemy==2.0.44
```

SQLite is included with Python, so no separate database server is required.

---

## 4. How to install and run the system

### Step 1: Open the project folder

Open a terminal or command prompt and go to the project directory:

```bash
cd SME_Invoice_System
```

### Step 2: Create a virtual environment

On Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

On macOS or Linux:

```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Run the Flask application

```bash
python app.py
```

After starting the application, open this address in the browser:

```text
http://127.0.0.1:5000/
```

The application starts with the included `invoice.db` demo database. If the database file is removed, the application will create the database tables automatically when it starts.

---

## 5. Demo data and database utilities

The following routes are included only for development and thesis demonstration. They should not be exposed in a production system.

Open these URLs in the browser while the app is running:

```text
http://127.0.0.1:5000/init-db
http://127.0.0.1:5000/seed-demo
http://127.0.0.1:5000/seed-additional-data
```

Purpose:

- `/init-db` creates database tables from the SQLAlchemy models.
- `/seed-demo` inserts a small initial synthetic dataset.
- `/seed-additional-data` inserts extra synthetic customers and invoices for testing and screenshots.

The seed routes are idempotent for the included demo records, meaning they check existing data before adding duplicates.

---

## 6. Main application pages

After running the application, these pages are available:

```text
/                         Home page
/dashboard                Dashboard and KPIs
/invoices                 Full invoice list
/invoices/due-soon        Invoices due in the next 7 days
/invoices/overdue         Overdue invoices
/invoices/new             Create new invoice
/customers                Customer list
/customers/new            Create new customer
/settings                 Default tax and currency settings
/export/invoices          Export invoices as CSV
```

---

## 7. How to run the offline analytics script

Make sure the Flask application has already created or contains `invoice.db`, then run:

```bash
python analytics.py
```

The script prints a simple management-style report to the terminal, including total customers, total invoices, total invoiced amount, unpaid amount, overdue amount, and overdue invoices.

---

## 8. Testing checklist

A simple manual test can be carried out as follows:

1. Open the home page.
2. Open the dashboard and check the KPI cards.
3. Open the customer list and create or edit a customer.
4. Create an invoice from `/invoices/new`.
5. Add one or more line items and check that subtotal, tax, and total are saved correctly.
6. Open the invoice list and search by invoice number or customer name.
7. Open the due-soon and overdue invoice views.
8. Mark an invoice as Paid and check that dashboard/overdue values change.
9. Export invoices as CSV using `/export/invoices`.
10. Run `python analytics.py` and compare the console report with the web dashboard.

---

## 9. Prototype limitations

The application is a research prototype. It intentionally excludes several production-level features:

- user authentication and role-based access control;
- legal invoice certification and tax authority reporting;
- accounting-system integration;
- payment gateway integration;
- bank reconciliation;
- audit logging;
- advanced validation and localization;
- production deployment hardening.

The purpose of the system is to demonstrate process digitalization and evaluation, not to replace certified invoicing or accounting software.

---


