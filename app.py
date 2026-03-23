from flask import Flask, render_template, request, redirect, url_for, make_response
from flask_sqlalchemy import SQLAlchemy
import os
import csv
import io
from datetime import date, timedelta, datetime
from sqlalchemy import or_  # used for search (invoice number OR customer name)


# =============================================================================
# SME Invoice System - Prototype for MSc thesis (Chaimae Binjach)
# -----------------------------------------------------------------------------
# This application is a lightweight web tool that supports basic invoice
# management for small and medium-sized enterprises (SMEs).
#
# Main design focus:
# - Keep the data model understandable (customers, invoices, items, settings)
# - Implement a simple invoice status lifecycle (Draft -> Sent -> Paid)
# - Highlight overdue receivables through filters and a dashboard
# - Demonstrate low-code/no-code ideas via configurable settings
#   instead of hard-coded tax rates and currencies.
# =============================================================================


app = Flask(__name__)

# --- Database configuration ---------------------------------------------------
# SQLite is used as an embedded database engine. For a prototype and thesis
# project this is sufficient and easy to distribute. For a production system
# the same code could be pointed at PostgreSQL or another RDBMS.

basedir = os.path.abspath(os.path.dirname(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(basedir, "invoice.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# --- Database models ----------------------------------------------------------
# The model layer represents the core business entities. These tables
# are small but correspond to typical SME needs.


class Customer(db.Model):
    """
    Stores SME customer / partner data.

    In a real deployment this table could be synchronised with a CRM or
    accounting system. Here it acts as master data for invoice generation.
    """
    __tablename__ = "customers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    tax_number = db.Column(db.String(50))
    address = db.Column(db.String(255))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(50))
    # default payment terms used when calculating due dates
    payment_terms_days = db.Column(db.Integer, default=30)
    is_active = db.Column(db.Boolean, default=True)

    def __repr__(self) -> str:
        return f"<Customer {self.name}>"


class Invoice(db.Model):
    """
    Invoice header: one record per invoice.

    Line-level detail (services/products) is stored separately in InvoiceItem.
    Financial totals (subtotal, tax, total) are stored here to keep
    reporting queries simple.
    """
    __tablename__ = "invoices"

    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)

    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False)
    customer = db.relationship("Customer", backref="invoices")

    issue_date = db.Column(db.Date, default=date.today)
    due_date = db.Column(db.Date, nullable=False)

    # Status lifecycle is intentionally simple for the thesis:
    # Draft -> Sent -> Paid
    # "Overdue" is not a separate stored state here. It is derived in
    # queries based on due_date + status != Paid.
    status = db.Column(db.String(20), default="Draft")  # Draft / Sent / Paid

    subtotal = db.Column(db.Float, nullable=False)
    tax_amount = db.Column(db.Float, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)

    currency = db.Column(db.String(10), default="HUF")
    notes = db.Column(db.Text)

    # One-to-many relationship: an invoice can have multiple items.
    items = db.relationship("InvoiceItem", backref="invoice", lazy=True)

    def __repr__(self) -> str:
        return f"<Invoice {self.invoice_number}>"


class InvoiceItem(db.Model):
    """
    Individual line items that belong to an invoice.

    This allows the system to represent multiple services or products
    within a single invoice, even though the prototype only allows up
    to three items in the form.
    """
    __tablename__ = "invoice_items"

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id"), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Float, nullable=False, default=1.0)
    unit_price = db.Column(db.Float, nullable=False, default=0.0)
    line_total = db.Column(db.Float, nullable=False, default=0.0)

    def __repr__(self) -> str:
        return f"<InvoiceItem {self.description}>"


class Settings(db.Model):
    """
    System-level configuration that can be changed through the web UI.

    This simulates a low-code style configuration where business users can
    adjust defaults (tax rate, currency) without modifying the source code.
    """
    __tablename__ = "settings"

    id = db.Column(db.Integer, primary_key=True)
    default_tax_percent = db.Column(db.Float, default=27.0)
    default_currency = db.Column(db.String(10), default="HUF")


def get_settings():
    """
    Helper: ensure there is exactly one Settings row and return it.

    If no settings record exists (e.g. in a fresh database), it creates one
    with default values. This is called whenever the business logic needs
    configuration values (for example in the invoice form).
    """
    settings = Settings.query.first()
    if not settings:
        settings = Settings(default_tax_percent=27.0, default_currency="HUF")
        db.session.add(settings)
        db.session.commit()
    return settings


# --- Core pages ---------------------------------------------------------------
# These routes deliver the main user-facing pages of the system.


@app.route("/")
def home():
    """Landing page with a short explanation and navigation cards."""
    return render_template("home.html")


@app.route("/dashboard")
def dashboard():
    """
    Simple KPI dashboard.

    Focus: provide management with basic aggregates to monitor cash flow:
    - number of customers
    - number of invoices
    - total invoiced amount
    - unpaid amount (Sent)
    - overdue amount + list of overdue invoices
    """
    today = date.today()

    # Count of master data and documents
    total_customers = Customer.query.count()
    total_invoices = Invoice.query.count()

    # Total invoiced amount across all invoices
    total_amount = db.session.query(db.func.sum(Invoice.total_amount)).scalar() or 0.0

    # Unpaid = invoices that were sent but not yet marked as paid
    unpaid_invoices = Invoice.query.filter(Invoice.status.in_(["Sent"])).all()
    total_unpaid = sum(inv.total_amount for inv in unpaid_invoices)

    # Overdue = not Paid and due date in the past
    overdue_invoices = (
        Invoice.query
        .join(Customer)
        .filter(Invoice.status != "Paid")
        .filter(Invoice.due_date < today)
        .order_by(Invoice.due_date.asc())
        .all()
    )
    total_overdue = sum(inv.total_amount for inv in overdue_invoices)

    return render_template(
        "dashboard.html",
        total_customers=total_customers,
        total_invoices=total_invoices,
        total_amount=total_amount,
        total_unpaid=total_unpaid,
        total_overdue=total_overdue,
        overdue_invoices=overdue_invoices,
    )


# --- DB utilities (development only) -----------------------------------------
# The following routes are not intended for a production installation.
# They are used to create and populate the database during development
# and for demonstration in the thesis.


@app.route("/init-db")
def init_db():
    """
    Initialise the database schema.

    Creates all tables based on the SQLAlchemy models.
    In production this endpoint should not be exposed over HTTP.
    """
    db.create_all()
    return "Database initialized ✅"


@app.route("/seed-demo")
def seed_demo():
    """
    Insert a small amount of demo data.

    This helps with initial testing and also provides data for screenshots
    in the thesis document.
    """
    # --- Customers ------------------------------------------------------------
    if Customer.query.count() == 0:
        # Two example SME customers
        c1 = Customer(
            name="Alpha Trade Kft",
            tax_number="12345678-1-42",
            address="Budapest, Example utca 1.",
            email="info@alphatrade.hu",
            phone="+36 30 111 1111",
            payment_terms_days=30,
        )
        c2 = Customer(
            name="Beta Solutions Bt",
            tax_number="87654321-2-13",
            address="Budapest, Demo utca 5.",
            email="hello@betasolutions.hu",
            phone="+36 30 222 2222",
            payment_terms_days=14,
        )
        db.session.add_all([c1, c2])
        db.session.commit()
    else:
        # Re-use first two customers if they already exist
        c1 = Customer.query.first()
        c2 = Customer.query.offset(1).first() or Customer.query.first()

    # --- Invoices + line items -----------------------------------------------
    if Invoice.query.count() == 0:
        today = date.today()

        # Overdue-style invoice (due date in the past, still Sent)
        inv1 = Invoice(
            invoice_number="2025-0001",
            customer=c1,
            issue_date=today - timedelta(days=20),
            due_date=today - timedelta(days=6),
            status="Sent",  # will be treated as overdue because due_date < today
            subtotal=100000,
            tax_amount=27000,
            total_amount=127000,
            currency="HUF",
            notes="Website and support package",
        )

        # Invoice that is still within the payment deadline
        inv2 = Invoice(
            invoice_number="2025-0002",
            customer=c2,
            issue_date=today - timedelta(days=10),
            due_date=today + timedelta(days=4),
            status="Sent",
            subtotal=50000,
            tax_amount=13500,
            total_amount=63500,
            currency="HUF",
            notes="Consulting engagement",
        )

        db.session.add_all([inv1, inv2])
        db.session.flush()  # ensure we have IDs for line items

        # Line items for inv1
        item1_1 = InvoiceItem(
            invoice=inv1,
            description="Website development",
            quantity=1,
            unit_price=80000,
            line_total=80000,
        )
        item1_2 = InvoiceItem(
            invoice=inv1,
            description="Maintenance & support",
            quantity=1,
            unit_price=20000,
            line_total=20000,
        )

        # Line items for inv2
        item2_1 = InvoiceItem(
            invoice=inv2,
            description="Consulting day rate",
            quantity=2,
            unit_price=25000,
            line_total=50000,
        )

        db.session.add_all([item1_1, item1_2, item2_1])
        db.session.commit()

    return "Demo data inserted ✅"


@app.route("/seed-additional-data")
def seed_additional_data():
    """
    Insert additional demo customers and invoices.

    This function is used to make the dataset richer for testing and
    screenshots. It can be called multiple times without duplicating data
    because it checks for existing customers and invoices.
    """
    # --- Extra customers ------------------------------------------------------
    extra_customers = [
        {
            "name": "Delta Logistics Kft",
            "tax_number": "56781234-2-51",
            "address": "Győr, Ipari park 3.",
            "email": "info@deltalogistics.hu",
            "phone": "+36 96 123 456",
            "payment_terms_days": 21,
        },
        {
            "name": "EcoPrint Studio Bt",
            "tax_number": "45678912-1-11",
            "address": "Budapest, Zöldmező utca 9.",
            "email": "hello@ecoprint.hu",
            "phone": "+36 30 456 7890",
            "payment_terms_days": 14,
        },
        {
            "name": "Nordic Consulting Bt",
            "tax_number": "99887766-2-42",
            "address": "Debrecen, Központi tér 7.",
            "email": "office@nordicconsulting.hu",
            "phone": "+36 52 555 777",
            "payment_terms_days": 30,
        },
    ]

    created_customers = []
    for data in extra_customers:
        existing = Customer.query.filter_by(name=data["name"]).first()
        if not existing:
            c = Customer(
                name=data["name"],
                tax_number=data["tax_number"],
                address=data["address"],
                email=data["email"],
                phone=data["phone"],
                payment_terms_days=data["payment_terms_days"],
                is_active=True,
            )
            db.session.add(c)
            created_customers.append(c)

    if created_customers:
        db.session.commit()

    # Reload all customers so we can reference them by name
    customers_by_name = {c.name: c for c in Customer.query.all()}
    today = date.today()

    # --- Extra invoices -------------------------------------------------------
    extra_invoices = [
        {
            "number": "2025-0004",
            "customer_name": "Delta Logistics Kft",
            "issue_offset_days": -15,
            "due_offset_days": -1,
            "status": "Sent",
            "subtotal": 120000,
            "tax_percent": 27,
            "currency": "HUF",
            "notes": "Transport services for November.",
        },
        {
            "number": "2025-0005",
            "customer_name": "EcoPrint Studio Bt",
            "issue_offset_days": -5,
            "due_offset_days": 10,
            "status": "Sent",
            "subtotal": 45000,
            "tax_percent": 27,
            "currency": "HUF",
            "notes": "Eco-friendly printing for marketing materials.",
        },
        {
            "number": "2025-0006",
            "customer_name": "Nordic Consulting Bt",
            "issue_offset_days": -30,
            "due_offset_days": -20,
            "status": "Paid",
            "subtotal": 80000,
            "tax_percent": 27,
            "currency": "HUF",
            "notes": "Consulting project – completed and paid.",
        },
    ]

    created_invoices = 0

    for data in extra_invoices:
        # Skip if invoice already exists (idempotent behaviour)
        existing = Invoice.query.filter_by(invoice_number=data["number"]).first()
        if existing:
            continue

        customer = customers_by_name.get(data["customer_name"])
        if not customer:
            # Safety check: if the customer is missing for some reason,
            # we simply skip this record.
            continue

        issue_date = today + timedelta(days=data["issue_offset_days"])
        due_date = today + timedelta(days=data["due_offset_days"])

        tax_amount = data["subtotal"] * (data["tax_percent"] / 100.0)
        total_amount = data["subtotal"] + tax_amount

        inv = Invoice(
            invoice_number=data["number"],
            customer=customer,
            issue_date=issue_date,
            due_date=due_date,
            status=data["status"],
            subtotal=data["subtotal"],
            tax_amount=tax_amount,
            total_amount=total_amount,
            currency=data["currency"],
            notes=data["notes"],
        )
        db.session.add(inv)
        db.session.flush()

        # Simple single line item for each new invoice
        item = InvoiceItem(
            invoice=inv,
            description=data["notes"],
            quantity=1,
            unit_price=data["subtotal"],
            line_total=data["subtotal"],
        )
        db.session.add(item)

        created_invoices += 1

    if created_invoices > 0:
        db.session.commit()

    return (
        f"Extra demo data inserted ✅ "
        f"(customers added: {len(created_customers)}, invoices added: {created_invoices})"
    )


# --- Invoice views ------------------------------------------------------------
# The routes below implement searching, filtering, creation, editing,
# and exporting of invoices.


@app.route("/invoices")
def list_invoices():
    """
    List all invoices with an optional search box.

    The search term is applied to both invoice number and customer name,
    which is a common requirement in SME back-office tools.
    """
    search_term = request.args.get("q", "").strip()

    # Base query joins customers so we can display names and filter on them
    query = Invoice.query.join(Customer).order_by(Invoice.issue_date.desc())

    if search_term:
        like = f"%{search_term}%"
        query = query.filter(
            or_(
                Invoice.invoice_number.ilike(like),
                Customer.name.ilike(like),
            )
        )

    invoices = query.all()

    return render_template(
        "invoices_list.html",
        invoices=invoices,
        view_title="Invoices",
        search_term=search_term,
    )


@app.route("/invoices/overdue")
def overdue_invoices():
    """
    List invoices that are considered overdue.

    Definition used in this prototype:
    - invoice is not Paid
    - due date is strictly in the past (before today)
    """
    today = date.today()
    search_term = request.args.get("q", "").strip()

    query = (
        Invoice.query
        .join(Customer)
        .filter(Invoice.status != "Paid")
        .filter(Invoice.due_date < today)
        .order_by(Invoice.due_date.asc())
    )

    if search_term:
        like = f"%{search_term}%"
        query = query.filter(
            or_(
                Invoice.invoice_number.ilike(like),
                Customer.name.ilike(like),
            )
        )

    invoices = query.all()

    return render_template(
        "invoices_list.html",
        invoices=invoices,
        view_title="Overdue invoices",
        search_term=search_term,
    )


@app.route("/invoices/due-soon")
def due_soon_invoices():
    """
    List invoices that are due in the next 7 days.

    This view supports proactive follow-up tasks before invoices become overdue.
    """
    today = date.today()
    limit = today + timedelta(days=7)
    search_term = request.args.get("q", "").strip()

    query = (
        Invoice.query
        .join(Customer)
        .filter(Invoice.status != "Paid")
        .filter(Invoice.due_date >= today)
        .filter(Invoice.due_date <= limit)
        .order_by(Invoice.due_date.asc())
    )

    if search_term:
        like = f"%{search_term}%"
        query = query.filter(
            or_(
                Invoice.invoice_number.ilike(like),
                Customer.name.ilike(like),
            )
        )

    invoices = query.all()

    return render_template(
        "invoices_list.html",
        invoices=invoices,
        view_title="Invoices due in the next 7 days",
        search_term=search_term,
    )


@app.route("/invoices/<int:invoice_id>")
def invoice_detail(invoice_id: int):
    """
    Print-friendly detail view of a single invoice.

    This page is designed so it can be printed directly or exported to PDF
    via the browser. It also shows the line items if present.
    """
    invoice = Invoice.query.get_or_404(invoice_id)
    return render_template("invoice_detail.html", invoice=invoice)


@app.route("/invoices/new", methods=["GET", "POST"])
def create_invoice():
    """
    Invoice creation form.

    The form supports:
    - manual subtotal entry, and/or
    - up to three optional line items.
      If line items are provided, they override the manual subtotal.
    """
    error = None
    customers = Customer.query.order_by(Customer.name.asc()).all()
    settings = get_settings()
    tax_percent_value = settings.default_tax_percent  # used to pre-fill the form

    if request.method == "POST":
        # Basic header fields from the form
        invoice_number = request.form.get("invoice_number", "").strip()
        customer_id_raw = request.form.get("customer_id", "").strip()
        issue_date_str = request.form.get("issue_date", "").strip()
        due_date_str = request.form.get("due_date", "").strip()
        status = request.form.get("status", "Draft").strip()
        currency = request.form.get("currency", "").strip() or settings.default_currency
        notes = request.form.get("notes", "").strip()

        # Numeric fields: manual subtotal and tax %
        subtotal_raw = request.form.get("subtotal", "0").replace(",", ".").strip()
        tax_percent_raw = (
            request.form.get("tax_percent", "")
            .replace(",", ".")
            .strip()
            or str(settings.default_tax_percent)
        )

        # Basic validation of required fields
        if not invoice_number:
            error = "Invoice number is required."
        elif not customer_id_raw:
            error = "Customer is required."
        else:
            # Resolve customer reference
            try:
                customer_id = int(customer_id_raw)
                customer = Customer.query.get(customer_id)
            except (ValueError, TypeError):
                customer = None

            # Convert subtotal to float (0.0 if invalid)
            try:
                subtotal = float(subtotal_raw)
            except ValueError:
                subtotal = 0.0

            # Collect optional line items and calculate subtotal_from_items
            line_items_data = []
            subtotal_from_items = 0.0

            for i in range(1, 4):
                desc = request.form.get(f"item_desc_{i}", "").strip()
                if not desc:
                    # Skip rows without description
                    continue

                qty_raw = request.form.get(f"item_qty_{i}", "1").replace(",", ".").strip()
                price_raw = request.form.get(f"item_price_{i}", "0").replace(",", ".").strip()

                try:
                    qty = float(qty_raw)
                except ValueError:
                    qty = 1.0

                try:
                    unit_price = float(price_raw)
                except ValueError:
                    unit_price = 0.0

                line_total = qty * unit_price
                subtotal_from_items += line_total

                line_items_data.append(
                    {
                        "description": desc,
                        "quantity": qty,
                        "unit_price": unit_price,
                        "line_total": line_total,
                    }
                )

            # If at least one item was entered, we trust the item-based subtotal
            if subtotal_from_items > 0:
                subtotal = subtotal_from_items

            # Parse tax percentage, fall back to settings if invalid
            try:
                tax_percent = float(tax_percent_raw)
            except ValueError:
                tax_percent = settings.default_tax_percent

            # Used when re-rendering the form after an error
            tax_percent_value = tax_percent

            # Final validation before saving
            if not customer:
                error = "Selected customer is invalid."
            elif subtotal <= 0:
                error = "Subtotal must be greater than zero (from field or items)."
            else:
                # --- Date parsing with fallbacks --------------------------------
                if issue_date_str:
                    try:
                        issue_date = datetime.fromisoformat(issue_date_str).date()
                    except ValueError:
                        issue_date = date.today()
                else:
                    issue_date = date.today()

                if due_date_str:
                    try:
                        due_date = datetime.fromisoformat(due_date_str).date()
                    except ValueError:
                        due_date = issue_date + timedelta(days=customer.payment_terms_days)
                else:
                    # Default: use customer-specific payment terms
                    due_date = issue_date + timedelta(days=customer.payment_terms_days)

                # Tax and total calculations
                tax_amount = subtotal * (tax_percent / 100.0)
                total_amount = subtotal + tax_amount

                # Create new invoice record
                new_invoice = Invoice(
                    invoice_number=invoice_number,
                    customer=customer,
                    issue_date=issue_date,
                    due_date=due_date,
                    status=status,
                    subtotal=subtotal,
                    tax_amount=tax_amount,
                    total_amount=total_amount,
                    currency=currency,
                    notes=notes,
                )
                db.session.add(new_invoice)
                db.session.flush()  # ensure new_invoice.id exists

                # Create line item rows if any items were entered
                for item in line_items_data:
                    ii = InvoiceItem(
                        invoice=new_invoice,
                        description=item["description"],
                        quantity=item["quantity"],
                        unit_price=item["unit_price"],
                        line_total=item["line_total"],
                    )
                    db.session.add(ii)

                db.session.commit()
                return redirect(url_for("list_invoices"))

    # GET request or form error: re-display the form
    return render_template(
        "invoice_form.html",
        error=error,
        customers=customers,
        settings=settings,
        mode="create",
        invoice=None,
        tax_percent_value=tax_percent_value,
    )


@app.route("/invoices/<int:invoice_id>/edit", methods=["GET", "POST"])
def edit_invoice(invoice_id: int):
    """
    Edit an existing invoice.

    We allow editing of:
    - header fields (customer, dates, status, tax, currency, notes, subtotal)
    - optional new line items (up to three)
      If new items are provided, existing items are replaced.
      If line item fields are left empty, existing items remain unchanged.
    """
    invoice = Invoice.query.get_or_404(invoice_id)
    error = None
    customers = Customer.query.order_by(Customer.name.asc()).all()
    settings = get_settings()

    # Try to derive approximate tax percent from stored values
    if invoice.subtotal and invoice.tax_amount:
        tax_percent_value = round((invoice.tax_amount / invoice.subtotal) * 100.0, 2)
    else:
        tax_percent_value = settings.default_tax_percent

    if request.method == "POST":
        invoice_number = request.form.get("invoice_number", "").strip()
        customer_id_raw = request.form.get("customer_id", "").strip()
        issue_date_str = request.form.get("issue_date", "").strip()
        due_date_str = request.form.get("due_date", "").strip()
        status = request.form.get("status", invoice.status).strip()
        currency = request.form.get("currency", "").strip() or settings.default_currency
        notes = request.form.get("notes", "").strip()

        subtotal_raw = request.form.get("subtotal", "0").replace(",", ".").strip()
        tax_percent_raw = request.form.get("tax_percent", "").replace(",", ".").strip()

        if not invoice_number:
            error = "Invoice number is required."
        elif not customer_id_raw:
            error = "Customer is required."
        else:
            # Resolve customer
            try:
                customer_id = int(customer_id_raw)
                customer = Customer.query.get(customer_id)
            except (ValueError, TypeError):
                customer = None

            # Start with existing subtotal, then override if needed
            try:
                subtotal = float(subtotal_raw)
            except ValueError:
                subtotal = invoice.subtotal or 0.0

            # Collect potential new line items
            line_items_data = []
            subtotal_from_items = 0.0

            for i in range(1, 4):
                desc = request.form.get(f"item_desc_{i}", "").strip()
                if not desc:
                    continue
                qty_raw = request.form.get(f"item_qty_{i}", "1").replace(",", ".").strip()
                price_raw = request.form.get(f"item_price_{i}", "0").replace(",", ".").strip()

                try:
                    qty = float(qty_raw)
                except ValueError:
                    qty = 1.0

                try:
                    unit_price = float(price_raw)
                except ValueError:
                    unit_price = 0.0

                line_total = qty * unit_price
                subtotal_from_items += line_total

                line_items_data.append(
                    {
                        "description": desc,
                        "quantity": qty,
                        "unit_price": unit_price,
                        "line_total": line_total,
                    }
                )

            # If new items exist, override subtotal
            if subtotal_from_items > 0:
                subtotal = subtotal_from_items

            # Tax percent logic: use user entry if valid, otherwise keep old
            if tax_percent_raw:
                try:
                    tax_percent = float(tax_percent_raw)
                except ValueError:
                    tax_percent = tax_percent_value
            else:
                tax_percent = tax_percent_value

            # Store for potential redisplay after error
            tax_percent_value = tax_percent

            if not customer:
                error = "Selected customer is invalid."
            elif subtotal <= 0:
                error = "Subtotal must be greater than zero (from field or items)."
            else:
                # Parse dates with sensible fallbacks
                if issue_date_str:
                    try:
                        issue_date = datetime.fromisoformat(issue_date_str).date()
                    except ValueError:
                        issue_date = invoice.issue_date or date.today()
                else:
                    issue_date = invoice.issue_date or date.today()

                if due_date_str:
                    try:
                        due_date = datetime.fromisoformat(due_date_str).date()
                    except ValueError:
                        due_date = invoice.due_date or (
                            issue_date + timedelta(days=customer.payment_terms_days)
                        )
                else:
                    due_date = invoice.due_date or (
                        issue_date + timedelta(days=customer.payment_terms_days)
                    )

                # Recalculate tax and total amounts
                tax_amount = subtotal * (tax_percent / 100.0)
                total_amount = subtotal + tax_amount

                # Update invoice header fields
                invoice.invoice_number = invoice_number
                invoice.customer = customer
                invoice.issue_date = issue_date
                invoice.due_date = due_date
                invoice.status = status
                invoice.subtotal = subtotal
                invoice.tax_amount = tax_amount
                invoice.total_amount = total_amount
                invoice.currency = currency
                invoice.notes = notes

                # Replace line items only if user entered new ones
                if line_items_data:
                    InvoiceItem.query.filter_by(invoice_id=invoice.id).delete()
                    for item in line_items_data:
                        ii = InvoiceItem(
                            invoice=invoice,
                            description=item["description"],
                            quantity=item["quantity"],
                            unit_price=item["unit_price"],
                            line_total=item["line_total"],
                        )
                        db.session.add(ii)

                db.session.commit()
                return redirect(url_for("list_invoices"))

    return render_template(
        "invoice_form.html",
        error=error,
        customers=customers,
        settings=settings,
        mode="edit",
        invoice=invoice,
        tax_percent_value=tax_percent_value,
    )


@app.route("/invoices/<int:invoice_id>/mark-paid", methods=["POST"])
def mark_invoice_paid(invoice_id: int):
    """
    Set the invoice status to 'Paid'.

    This route represents the typical workflow where a payment is
    received and the open receivable is closed.
    """
    invoice = Invoice.query.get_or_404(invoice_id)
    invoice.status = "Paid"
    db.session.commit()
    return redirect(url_for("list_invoices"))


@app.route("/invoices/<int:invoice_id>/mark-sent", methods=["POST"])
def mark_invoice_sent(invoice_id: int):
    """
    Undo operation for 'Paid': set status back to 'Sent'.

    This is useful if a payment was recorded by mistake or if the invoice
    needs to be re-opened for some reason.
    """
    invoice = Invoice.query.get_or_404(invoice_id)
    invoice.status = "Sent"
    db.session.commit()
    return redirect(url_for("list_invoices"))


@app.route("/export/invoices")
def export_invoices():
    """
    Export all invoices to a CSV file.

    Typical use cases:
    - provide data for an accountant
    - import invoices into another system
    - perform further analysis in Excel.
    """
    invoices = Invoice.query.order_by(Invoice.issue_date.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)

    # Header row for the CSV file
    writer.writerow(
        [
            "Invoice number",
            "Customer",
            "Issue date",
            "Due date",
            "Status",
            "Subtotal",
            "Tax amount",
            "Total amount",
            "Currency",
            "Notes",
        ]
    )

    for inv in invoices:
        writer.writerow(
            [
                inv.invoice_number,
                inv.customer.name if inv.customer else "",
                inv.issue_date.isoformat(),
                inv.due_date.isoformat(),
                inv.status,
                f"{inv.subtotal:.2f}",
                f"{inv.tax_amount:.2f}",
                f"{inv.total_amount:.2f}",
                inv.currency,
                # Notes are flattened into a single line for CSV readability
                (inv.notes or "").replace("\n", " "),
            ]
        )

    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=invoices.csv"
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    return response


# --- Customer views -----------------------------------------------------------
# CRUD operations for customer master data.


@app.route("/customers")
def list_customers():
    """List all customers ordered alphabetically by name."""
    customers = Customer.query.order_by(Customer.name.asc()).all()
    return render_template("customers_list.html", customers=customers)


@app.route("/customers/new", methods=["GET", "POST"])
def create_customer():
    """
    Create a new customer record.

    This mirrors a simple onboarding process for a new SME client or
    business partner.
    """
    error = None

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        tax_number = request.form.get("tax_number", "").strip()
        address = request.form.get("address", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        payment_terms_days_raw = request.form.get("payment_terms_days", "30").strip()

        if not name:
            error = "Name is required."
        else:
            try:
                payment_terms_days = int(payment_terms_days_raw)
            except ValueError:
                # Fallback: use default 30 days if user input is not valid
                payment_terms_days = 30

            new_customer = Customer(
                name=name,
                tax_number=tax_number,
                address=address,
                email=email,
                phone=phone,
                payment_terms_days=payment_terms_days,
                is_active=True,
            )
            db.session.add(new_customer)
            db.session.commit()
            return redirect(url_for("list_customers"))

    return render_template("customer_form.html", error=error, mode="create", customer=None)


@app.route("/customers/<int:customer_id>/edit", methods=["GET", "POST"])
def edit_customer(customer_id: int):
    """
    Edit an existing customer.

    Typical use case: updating contact details or adjusting payment terms
    following a change in commercial agreements.
    """
    customer = Customer.query.get_or_404(customer_id)
    error = None

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        tax_number = request.form.get("tax_number", "").strip()
        address = request.form.get("address", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        payment_terms_days_raw = request.form.get("payment_terms_days", "30").strip()
        is_active_raw = request.form.get("is_active", "on")

        if not name:
            error = "Name is required."
        else:
            try:
                payment_terms_days = int(payment_terms_days_raw)
            except ValueError:
                payment_terms_days = customer.payment_terms_days

            # Update fields in place
            customer.name = name
            customer.tax_number = tax_number
            customer.address = address
            customer.email = email
            customer.phone = phone
            customer.payment_terms_days = payment_terms_days
            customer.is_active = is_active_raw == "on"

            db.session.commit()
            return redirect(url_for("list_customers"))

    return render_template("customer_form.html", error=error, mode="edit", customer=customer)


# --- Settings (LCNC-style configuration) --------------------------------------


@app.route("/settings", methods=["GET", "POST"])
def system_settings():
    """
    Settings page where the user can adjust default tax and currency.

    Currency logic:
    - User chooses a value from a small dropdown (HUF, EUR, USD, GBP, OTHER).
    - If OTHER is selected, the free text field "default_currency" is used.
    - Otherwise, the dropdown value is taken as the currency code.
    """
    settings = get_settings()
    message = None

    if request.method == "POST":
        # --- Tax value --------------------------------------------------------
        tax_raw = request.form.get("default_tax_percent", "").replace(",", ".").strip()

        try:
            tax_value = float(tax_raw)
        except ValueError:
            # If parsing fails, keep previous value
            tax_value = settings.default_tax_percent

        # --- Currency selection ----------------------------------------------
        # The dropdown name
        currency_choice = request.form.get("currency_choice", "").strip()
        # Potential custom code from the text field
        custom_currency = request.form.get("default_currency", "").strip()

        if currency_choice and currency_choice != "OTHER":
            # One of the common options (HUF, EUR, USD, GBP)
            currency = currency_choice
        else:
            # "OTHER" selected or nothing selected: use the typed custom code
            currency = custom_currency or settings.default_currency or "HUF"

        # Persist values
        settings.default_tax_percent = tax_value
        settings.default_currency = currency
        db.session.commit()
        message = "Settings saved successfully."

    return render_template("settings.html", settings=settings, message=message)


# --- Application entry point --------------------------------------------------


if __name__ == "__main__":
    # Ensure all tables exist before serving requests.
    # This keeps setup simple when running the prototype locally.
    with app.app_context():
        db.create_all()
    app.run(debug=True)
