"""
Offline analytics script for the SME Invoice System.

This script is intentionally kept outside the Flask web application.
It connects to the same SQLite database and reuses the SQLAlchemy models
from app.py to generate a small management-style report.

In the thesis, this file demonstrates that:
- once data is captured digitally,
- it can be reused easily for reporting and decision support
  without changing the core application.
"""

from datetime import date
from app import db, Customer, Invoice  # reuse database connection and models from the main app


def run_basic_report() -> None:
    """
    Compute and print a small set of key indicators to the console.

    Indicators:
    - Total number of customers
    - Total number of invoices
    - Total invoiced amount
    - Total unpaid amount (invoices with status "Sent")
    - Total overdue amount (not Paid and past due date)
    - List of overdue invoices (if any)

    This is a very simple example of offline analytics, but for an SME
    it already provides useful insight into the receivables situation.
    """
    today = date.today()

    # --- Basic counts ---------------------------------------------------------
    total_customers = Customer.query.count()
    total_invoices = Invoice.query.count()

    # Sum of all invoice totals (regardless of status)
    total_amount = db.session.query(db.func.sum(Invoice.total_amount)).scalar() or 0.0

    # --- Unpaid and overdue logic --------------------------------------------
    # Unpaid: invoices that were sent but not yet marked as paid.
    unpaid_invoices = Invoice.query.filter(Invoice.status.in_(["Sent"])).all()
    total_unpaid = sum(inv.total_amount for inv in unpaid_invoices)

    # Overdue: not Paid and due date strictly in the past.
    overdue_invoices = (
        Invoice.query
        .filter(Invoice.status != "Paid")
        .filter(Invoice.due_date < today)
        .all()
    )
    total_overdue = sum(inv.total_amount for inv in overdue_invoices)

    # --- Console output -------------------------------------------------------
    # The output is text-based on purpose so that it can be copied into
    # the thesis as an example, or pasted into e-mails / documents.
    print("=== SME Invoice Analytics ===")
    print(f"Total customers: {total_customers}")
    print(f"Total invoices: {total_invoices}")
    print(f"Total invoiced amount: {total_amount:.2f} HUF")
    print(f"Total unpaid (Sent): {total_unpaid:.2f} HUF")
    print(f"Total overdue amount: {total_overdue:.2f} HUF\n")

    if overdue_invoices:
        print("Overdue invoices:")
        for inv in overdue_invoices:
            print(
                f"- {inv.invoice_number} | {inv.customer.name} | "
                f"Due: {inv.due_date.isoformat()} | {inv.total_amount:.2f} {inv.currency}"
            )
    else:
        print("There are currently no overdue invoices.")


if __name__ == "__main__":
    """
    Entry point when the script is run directly, e.g.:

        python analytics.py

    Because the models and database session come from the Flask application
    (app.py), we need an application context. Once that is active, normal
    SQLAlchemy queries can be executed and the report can be generated.
    """
    from app import app as flask_app

    # Create an application context so that SQLAlchemy can access the database
    with flask_app.app_context():
        run_basic_report()
