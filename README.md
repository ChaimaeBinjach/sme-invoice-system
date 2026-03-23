# SME Invoice System

A lightweight invoice management web application built with **Python**, **Flask**, **SQLite**, and **Flask-SQLAlchemy**.

This project was developed as a prototype to demonstrate how a small or medium-sized enterprise (SME) can manage customer data, create and track invoices, monitor receivables, and generate simple analytics from the same dataset.

The aim of the project is to keep the system practical, understandable, and easy to use while still reflecting common real-world back-office needs such as invoice lifecycle tracking, overdue monitoring, configurable defaults, and reporting.

---

## About the Project

Many SMEs still handle invoice-related tasks in a fragmented way, using spreadsheets, manual tracking, or disconnected tools. This application was designed as a simple and focused alternative: one place to store customer records, create invoices, track their status, and monitor unpaid or overdue receivables.

The project also demonstrates that once business data is captured digitally, it can be reused not only inside the main application, but also for reporting and decision support.

---

## Main Features

### Customer Management
- Create and manage customer records
- Store business details such as:
  - name
  - tax number
  - address
  - e-mail
  - phone number
  - payment terms
- Edit customer information when needed

### Invoice Management
- Create new invoices
- Edit existing invoices
- Assign invoices to customers
- Add invoice notes
- Set issue date and due date
- Track invoice status through a simple lifecycle:
  - Draft
  - Sent
  - Paid

### Invoice Line Items
- Add up to three optional line items in the invoice form
- Automatically calculate line totals
- Use item-based subtotal calculation when line items are entered
- Recalculate tax and final total automatically

### Dashboard and Receivables Monitoring
- View a simple dashboard with key indicators
- Monitor:
  - total number of customers
  - total number of invoices
  - total invoiced amount
  - unpaid amount
  - overdue amount
- Display overdue invoices for quick follow-up

### Smart Invoice Views
- List all invoices
- Search invoices by invoice number or customer name
- View overdue invoices
- View invoices due in the next 7 days
- Open a print-friendly invoice detail page

### Export and Reporting
- Export invoice data to CSV
- Reuse the same database in a separate analytics script
- Generate a basic text-based management report from stored data

### Configurable System Settings
- Change default tax percentage
- Change default currency
- Demonstrate a low-code / no-code style approach where business users can adjust defaults without changing the source code

---

## Technologies Used

- **Python**
- **Flask**
- **Flask-SQLAlchemy**
- **SQLite**
- **SQLAlchemy**
- **HTML / Jinja templates**
- **CSV export**

---

## Project Structure

```bash
.
├── app.py
├── analytics.py
├── invoice.db
├── requirements.txt
├── .gitignore
├── templates/
└── README.md