# Python Imports

from flask import Flask, render_template, session
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask import request
from flask import redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
import random, math
from decimal import Decimal
from datetime import datetime, time as dtime
import time
from decimal import Decimal
import threading

app = Flask(__name__)
bootstrap = Bootstrap5(app)

# Database Config
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SESSION_COOKIE_SAMESITE'] = "Lax"
app.config['SESSION_COOKIE_SECURE'] = False

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://admin:ZINaRQfPPDqHAA0OP62M@my-rds-instance.cubaeu46y77l.us-east-1.rds.amazonaws.com:3306/flask_project' # Edit SQL login for local machine
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)

# User model creation for database and login

class Users(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
    role = db.Column(db.String(50), default="user", nullable=False)
    portfolio = db.relationship('Portfolio', backref='user', lazy=True)

# Stock model creation for database

class Stocks(db.Model):
    __tablename__ = 'stocks'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    ticker_symbol = db.Column(db.String(10), unique=True, nullable=False)
    price = db.Column(db.Numeric(10,2), nullable=False)
    day_high = db.Column(db.Numeric(10,2), nullable=False)
    day_low = db.Column(db.Numeric(10,2), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    market_cap = db.Column(db.Numeric(15,2), default=0.00)
    opening_price = db.Column(db.Numeric(10,2), default=0.00)
     
# Portfolio model creation for database

class Portfolio(db.Model):
    __tablename__ = 'portfolio'
    portfolio_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    stock_id = db.Column(db.Integer, db.ForeignKey('stocks.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    purchase_price = db.Column(db.Numeric(10,2), nullable=False)
    current_price = db.Column(db.Numeric(10,2), nullable=False)
    stock = db.relationship("Stocks", backref="portfolios", lazy=True)

# Transactions model creation for database

class Transactions(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    stock_symbol = db.Column(db.String(10), nullable=False)
    transaction_type = db.Column(db.String(10), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Numeric(10,2), nullable=False)
    total_amount = db.Column(db.Numeric(10,2), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('Users', backref='transactions', lazy=True)

#Creates a model for the balance
class Balance(db.Model):
    __tablename__ = 'balance'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    balance = db.Column(db.Numeric(10,2), nullable=False, default=0.00)
    user = db.relationship('Users', backref=db.backref('balance', uselist=False))

# Market hours settings 
class MarketHours(db.Model):
    __tablename__ = 'market_hours'
    id = db.Column(db.Integer, primary_key=True)
    market_open = db.Column(db.String(5), default="09:30")
    market_close = db.Column(db.String(5), default="16:00")
    market_open_time = db.Column(db.Time, default=dtime(9, 30))
    market_close_time = db.Column(db.Time, default=dtime(16, 0))

# Market holidays settings
class MarketHoliday(db.Model):
    __tablename__ = 'market_holidays'
    id = db.Column(db.Integer, primary_key=True)
    holiday_date = db.Column(db.Date, unique=True, nullable=False)
    description = db.Column(db.String(255))
    
#Price Random Generator / Auto-Triggers every 10s ($-0.09 --> $0.09 price)
#Stock Day High/Low, Market Cap, and Opening Price Functions also included in Randomizer

def randomizer():
    with app.app_context():
        stocks = Stocks.query.all()
        transactions = Transactions.query.all()
        portfolios = Portfolio.query.all()

        for stock in stocks:
            price_change = Decimal(random.uniform(-0.09, 0.09))
            stock.price = max(Decimal(stock.price) + price_change, Decimal("1.00"))

            if stock.opening_price is None or stock.opening_price == Decimal("0.00"):
                stock.opening_price = stock.price

            stock.market_cap = stock.quantity * stock.price

            if stock.day_high is None or stock.price > stock.day_high:
                stock.day_high = stock.price
            if stock.day_low is None or stock.price < stock.day_low:
                stock.day_low = stock.price

        for transaction in transactions:
            for stock in stocks:
                if stock.ticker_symbol == transaction.stock_symbol:
                    transaction.price = stock.price

        for portfolio in portfolios:
            for stock in stocks:
                if stock.id == portfolio.stock_id:
                    portfolio.current_price = stock.price

        db.session.commit()

    threading.Timer(10, randomizer).start()

# Creates table for the database

with app.app_context():
    db.create_all()
    randomizer()

# User loader to retrieve id numbers

@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))

# Helper Function for Market Hours
def is_market_open():
    now = datetime.now()
    weekday = now.weekday()
    
    # Market is closed on weekends
    if weekday >= 5:
        return False

    # Check if today is a holiday
    holiday = MarketHoliday.query.filter_by(holiday_date=now.date()).first()
    if holiday:
        return False

    # Use market hours from the session or default to 9:30 AM - 4:00 PM
    open_time = session.get("market_open", "09:00")
    close_time = session.get("market_close", "16:00")
    open_dt = datetime.strptime(open_time, "%H:%M").time()
    close_dt = datetime.strptime(close_time, "%H:%M").time()
    
    return open_dt <= now.time() <= close_dt

#Shared default, login, sign-up, and logout HTML pages between users and admins

@app.route('/')
def home():
    return render_template("login.html")

@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = Users.query.filter_by(username=request.form.get("username")).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            if user.role == "admin":
                return redirect(url_for("admin_dashboard"))
            else:
                return redirect(url_for("user_portfolio"))
        else:
            flash("Invalid login information", "danger")
    return render_template("login.html")          

@app.route('/sign_up', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        hashed = generate_password_hash(request.form.get("password"), method='pbkdf2:sha256')
        user = Users(
            username=request.form.get("username"),
            password=hashed,
            role="user"
        )
        db.session.add(user)
        db.session.commit()
        return redirect(url_for("login"))
    return render_template("sign_up.html")

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for("login"))

#User exclusive HTML pages

@app.route('/user_home', methods=["GET", "POST"])
def user_home():
    stocks = Stocks.query.all()
    return render_template('user_home.html', stocks=stocks)

@app.route('/user_portfolio')
@login_required
def user_portfolio():
    # Retrieve the user's cash balance (defaulting to 0 if none exists)
    user_balance = Balance.query.filter_by(user_id=current_user.id).first()
    cash_balance = user_balance.balance if user_balance else Decimal("0.00")

    # Retrieve all portfolio entries (stocks owned) for the user
    portfolio_entries = Portfolio.query.filter_by(user_id=current_user.id).all()
    
    # Calculate the total value of stock holdings
    stocks_total = Decimal("0.00")
    for entry in portfolio_entries:
        stocks_total += entry.quantity * entry.current_price

    # Total portfolio value is the sum of cash balance and stock holdings
    total_portfolio_value = cash_balance + stocks_total

    # Retrieve transaction history (if needed on this page)
    transactions = Transactions.query.filter_by(user_id=current_user.id).all()

    return render_template(
        'user_portfolio.html',
        cash_balance=cash_balance,
        portfolio_total=total_portfolio_value,
        portfolio=portfolio_entries,
        transactions=transactions
    )


@app.route('/user_trades', methods=["GET", "POST"])
@login_required
def user_trades():
    if request.method == "POST":
        action = request.form.get("action")

        # For both buy and sell actions, extract stock symbol and quantity
        if action in ["buy", "sell"]:
            if not is_market_open():
                flash("Market is currently closed. Trading is allowed only during market hours.", "warning")
                return redirect(url_for("user_trades"))
            if action == "buy":
                stock_symbol = request.form.get("buyStockSymbol", "").strip().upper()
                quantity_str = request.form.get("buyQuantity", "").strip()
            else:  # action == "sell"
                stock_symbol = request.form.get("sellStockSymbol", "").strip().upper()
                quantity_str = request.form.get("sellQuantity", "").strip()

            if not stock_symbol:
                flash("Stock symbol is required.", "danger")
                return redirect(url_for("user_trades"))

            if not quantity_str.isdigit():
                flash("Invalid quantity. Please enter a valid number.", "danger")
                return redirect(url_for("user_trades"))

            quantity = int(quantity_str)
            stock = Stocks.query.filter_by(ticker_symbol=stock_symbol).first()
            if not stock:
                flash("Stock not found. Please enter a valid stock symbol.", "danger")
                return redirect(url_for("user_trades"))

            total_price = stock.price * quantity

            if action == "buy":
                # Save pending purchase transaction in session
                session["pending_transaction"] = {
                    "action": "buy",
                    "stock_symbol": stock_symbol,
                    "quantity": quantity,
                    "total_price": str(total_price)
                }
                session.modified = True
                flash(f"Are you sure you want to buy {quantity} shares of {stock_symbol} for ${total_price:.2f}?", "warning")
                return redirect(url_for("user_trades"))
            
            if action == "sell":
                # Ensure the user has enough shares to sell
                user_stock = Portfolio.query.filter_by(user_id=current_user.id, stock_id=stock.id).first()
                if not user_stock or user_stock.quantity < quantity:
                    flash("You do not have enough shares to sell.", "danger")
                    return redirect(url_for("user_trades"))
                # Save pending sale transaction in session
                session["pending_transaction"] = {
                    "action": "sell",
                    "stock_symbol": stock_symbol,
                    "quantity": quantity,
                    "total_price": str(total_price)
                }
                session.modified = True
                flash(f"Are you sure you want to sell {quantity} shares of {stock_symbol} for ${total_price:.2f}?", "warning")
                return redirect(url_for("user_trades"))

        # Confirm Purchase Action
        elif action == "confirm_purchase":
            transaction = session.get("pending_transaction")
            if not transaction:
                flash("Transaction not found. Please try again.", "danger")
                return redirect(url_for("user_trades"))

            stock_symbol = transaction.get("stock_symbol")
            quantity = transaction.get("quantity")
            total_price = Decimal(transaction.get("total_price"))

            stock = Stocks.query.filter_by(ticker_symbol=stock_symbol).first()
            if not stock:
                flash("Stock no longer available.", "danger")
                return redirect(url_for("user_trades"))

            user_balance = Balance.query.filter_by(user_id=current_user.id).first()
            if not user_balance or user_balance.balance < total_price:
                flash("Insufficient funds to complete the purchase.", "danger")
                session.pop("pending_transaction", None)
                return redirect(url_for("user_trades"))

            # Deduct funds
            user_balance.balance -= total_price

            #Deduct stock quantity
            stock.quantity -= quantity

            # Create a transaction record
            new_transaction = Transactions(
                user_id=current_user.id,
                stock_symbol=stock_symbol,
                transaction_type="buy",
                quantity=quantity,
                price=stock.price,
                total_amount=total_price
            )

            # Update or add portfolio entry
            user_stock = Portfolio.query.filter_by(user_id=current_user.id, stock_id=stock.id).first()
            if user_stock:
                user_stock.quantity += quantity
                user_stock.current_price = stock.price
            else:
                new_portfolio_entry = Portfolio(
                    user_id=current_user.id,
                    stock_id=stock.id,
                    quantity=quantity,
                    purchase_price=stock.price,
                    current_price=stock.price
                )
                db.session.add(new_portfolio_entry)

            db.session.add(new_transaction)
            db.session.commit()
            session.pop("pending_transaction", None)
            flash(f"Successfully bought {quantity} shares of {stock_symbol}!", "success")
            return redirect(url_for("user_trades"))

        # Cancel Purchase Action
        elif action == "cancel_purchase":
            session.pop("pending_transaction", None)
            flash("Purchase canceled.", "info")
            return redirect(url_for("user_trades"))

        # Confirm Sell Action
        elif action == "confirm_sell":
            transaction = session.get("pending_transaction")
            if not transaction:
                flash("Transaction not found. Please try again.", "danger")
                return redirect(url_for("user_trades"))

            stock_symbol = transaction.get("stock_symbol")
            quantity = transaction.get("quantity")
            total_price = Decimal(transaction.get("total_price"))

            stock = Stocks.query.filter_by(ticker_symbol=stock_symbol).first()
            if not stock:
                flash("Stock no longer available.", "danger")
                return redirect(url_for("user_trades"))

            user_stock = Portfolio.query.filter_by(user_id=current_user.id, stock_id=stock.id).first()
            if not user_stock or user_stock.quantity < quantity:
                flash("You do not have enough shares to sell.", "danger")
                return redirect(url_for("user_trades"))

            # Deduct shares from the portfolio
            user_stock.quantity -= quantity
            if user_stock.quantity == 0:
                db.session.delete(user_stock)

            # Add funds from sale to the user's balance
            user_balance = Balance.query.filter_by(user_id=current_user.id).first()
            if not user_balance:
                user_balance = Balance(user_id=current_user.id, balance=0.00)
                db.session.add(user_balance)
                db.session.commit()

            #Adds money to the users account
            user_balance.balance += total_price

            #Adds sold quantity back to the stock quantity
            stock.quantity += quantity

            new_transaction = Transactions(
                user_id=current_user.id,
                stock_symbol=stock_symbol,
                transaction_type="sell",
                quantity=quantity,
                price=stock.price,
                total_amount=total_price
            )
            db.session.add(new_transaction)
            db.session.commit()
            session.pop("pending_transaction", None)
            flash(f"Successfully sold {quantity} shares of {stock_symbol} for ${total_price:.2f}!", "success")
            return redirect(url_for("user_trades"))

        # Cancel Sell Action
        elif action == "cancel_sell":
            session.pop("pending_transaction", None)
            flash("Sell transaction canceled.", "info")
            return redirect(url_for("user_trades"))

    # On GET, load available stocks and the users balance, then render the page.
    stocks = Stocks.query.all()
    user_balance = Balance.query.filter_by(user_id=current_user.id).first()
    cash_balance = user_balance.balance if user_balance else Decimal("0.00")

    return render_template("user_trades.html", stocks=stocks, balance=cash_balance)

@app.route('/user_transactions')
@login_required
def user_transactions():
    transactions = Transactions.query.filter_by(user_id=current_user.id).all()
    return render_template('user_transactions.html', transactions=transactions)

@app.route('/user_deposit', methods=["GET", "POST"])
@login_required
def user_deposit():
    if request.method == "POST":
        action = request.form.get("action")
        
        # Confirm or cancel pending deposit/withdrawal actions
        if action == "confirm_deposit":
            pending = session.get("pending_cash_transaction")
            if not pending or pending.get("action") != "deposit":
                flash("No pending deposit transaction.", "danger")
                return redirect(url_for("user_deposit"))
            amount = Decimal(pending.get("amount"))
            user_balance = Balance.query.filter_by(user_id=current_user.id).first()
            if not user_balance:
                user_balance = Balance(user_id=current_user.id, balance=0.00)
                db.session.add(user_balance)
                db.session.commit()
            user_balance.balance += amount
            db.session.commit()
            session.pop("pending_cash_transaction", None)
            flash(f"Successfully deposited ${amount:.2f}.", "success")
            return redirect(url_for("user_deposit"))
        
        elif action == "cancel_deposit":
            session.pop("pending_cash_transaction", None)
            flash("Deposit canceled.", "info")
            return redirect(url_for("user_deposit"))
        
        elif action == "confirm_withdraw":
            pending = session.get("pending_cash_transaction")
            if not pending or pending.get("action") != "withdraw":
                flash("No pending withdrawal transaction.", "danger")
                return redirect(url_for("user_deposit"))
            amount = Decimal(pending.get("amount"))
            user_balance = Balance.query.filter_by(user_id=current_user.id).first()
            if not user_balance or user_balance.balance < amount:
                flash("Insufficient funds to complete withdrawal.", "danger")
                session.pop("pending_cash_transaction", None)
                return redirect(url_for("user_deposit"))
            user_balance.balance -= amount
            db.session.commit()
            session.pop("pending_cash_transaction", None)
            flash(f"Successfully withdrew ${amount:.2f}.", "success")
            return redirect(url_for("user_deposit"))
        
        elif action == "cancel_withdraw":
            session.pop("pending_cash_transaction", None)
            flash("Withdrawal canceled.", "info")
            return redirect(url_for("user_deposit"))
        
        # Confirm deposit or withdrawal
        amount_str = request.form.get("amount", "").strip()
        try:
            amount = Decimal(amount_str)
        except ValueError:
            flash("Invalid amount entered.", "danger")
            return redirect(url_for("user_deposit"))
            
        if amount <= 0:
            flash("Please enter a positive amount.", "danger")
            return redirect(url_for("user_deposit"))
        
        if action == "deposit":
            session["pending_cash_transaction"] = {
                "action": "deposit",
                "amount": str(amount)
            }
            session.modified = True
            flash(f"Are you sure you want to deposit ${amount:.2f}?", "warning")
            return redirect(url_for("user_deposit"))
        
        elif action == "withdraw":
            user_balance = Balance.query.filter_by(user_id=current_user.id).first()
            if not user_balance or user_balance.balance < amount:
                flash("Insufficient funds to withdraw.", "danger")
                return redirect(url_for("user_deposit"))
            session["pending_cash_transaction"] = {
                "action": "withdraw",
                "amount": str(amount)
            }
            session.modified = True
            flash(f"Are you sure you want to withdraw ${amount:.2f}?", "warning")
            return redirect(url_for("user_deposit"))
    
    user_balance = Balance.query.filter_by(user_id=current_user.id).first()
    if not user_balance:
        user_balance = Balance(user_id=current_user.id, balance=0.00)
        db.session.add(user_balance)
        db.session.commit()
        
    return render_template("user_deposit.html", balance=user_balance.balance)

#Admin exclusive HTML pages

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    #checks if the current user has the admin role, if not redirects the user back to login
    if current_user.role != "admin":
        flash("Access denied.", "danger")
        return redirect(url_for("login"))

    #Retrieves the needed data
    users = Users.query.all()
    stocks = Stocks.query.all()
    transactions = Transactions.query.all()

    #Passes the data to the HTML file
    return render_template('admin_dashboard.html', users=users, stocks=stocks, transactions=transactions)

@app.route('/admin_stock_management', methods=["GET", "POST"])
@login_required
def admin_stock_management():
    if current_user.role != "admin":
        flash("Access denied.", "danger")
        return redirect(url_for("login"))
    
    if request.method == "POST":
        form_type = request.form.get("form_type")
        action = request.form.get("action")
        
        # Create stock
        if form_type == "create_stock":
            if action == "save_stock":
                session["pending_stock"] = {
                    "company_name": request.form.get("company_name"),
                    "ticker": request.form.get("ticker").upper(),
                    "quantity": request.form.get("quantity"),
                    "price": request.form.get("price")
                }
                flash(f"Are you sure you want to create stock {session['pending_stock']['ticker']} for {session['pending_stock']['company_name']}?", "warning")
                return redirect(url_for("admin_stock_management"))
            elif action == "confirm_stock":
                pending = session.pop("pending_stock", None)
                if pending:
                    if Stocks.query.filter((Stocks.name == pending["company_name"]) | (Stocks.ticker_symbol == pending["ticker"])).first():
                        flash("Stock already exists with this name or ticker.", "danger")
                    else:
                        new_stock = Stocks(
                            name=pending["company_name"],
                            ticker_symbol=pending["ticker"],
                            price=Decimal(pending["price"]),
                            day_high=Decimal(pending["price"]),
                            day_low=Decimal(pending["price"]),
                            quantity=int(pending["quantity"])
                        )
                        db.session.add(new_stock)
                        db.session.commit()
                        flash(f"Stock {pending['ticker']} created successfully!", "success")
                else:
                    flash("No pending stock creation found.", "danger")
                return redirect(url_for("admin_stock_management"))
            elif action == "cancel_stock":
                session.pop("pending_stock", None)
                flash("Stock creation canceled.", "info")
                return redirect(url_for("admin_stock_management"))
        
        # delete Stock
        elif form_type == "delete_stock":
            if action == "save_delete":
                session["pending_delete"] = {
                    "ticker": request.form.get("ticker").upper()
                }
                flash(f"Are you sure you want to delete stock {session['pending_delete']['ticker']}?", "warning")
                return redirect(url_for("admin_stock_management"))
            elif action == "confirm_delete":
                pending = session.pop("pending_delete", None)
                if pending:
                    stock = Stocks.query.filter_by(ticker_symbol=pending["ticker"]).first()
                    if stock:
                        db.session.delete(stock)
                        db.session.commit()
                        flash(f"Stock {stock.ticker_symbol} deleted successfully!", "success")
                    else:
                        flash("Stock not found.", "danger")
                else:
                    flash("No pending stock deletion found.", "danger")
                return redirect(url_for("admin_stock_management"))
            elif action == "cancel_delete":
                session.pop("pending_delete", None)
                flash("Stock deletion canceled.", "info")
                return redirect(url_for("admin_stock_management"))
        
        # Update Stock Price
        elif form_type == "update_stock":
            if action == "save_update":
                session["pending_update"] = {
                    "ticker": request.form.get("ticker").upper(),
                    "new_price": request.form.get("new_price")
                }
                flash(f"Are you sure you want to update stock {session['pending_update']['ticker']} to price {session['pending_update']['new_price']}?", "warning")
                return redirect(url_for("admin_stock_management"))
            elif action == "confirm_update":
                pending = session.pop("pending_update", None)
                if pending:
                    stock = Stocks.query.filter_by(ticker_symbol=pending["ticker"]).first()
                    if stock:
                        stock.price = Decimal(pending["new_price"])
                        db.session.commit()
                        flash(f"Price for {stock.ticker_symbol} updated successfully!", "success")
                    else:
                        flash("Stock not found.", "danger")
                else:
                    flash("No pending update found.", "danger")
                return redirect(url_for("admin_stock_management"))
            elif action == "cancel_update":
                session.pop("pending_update", None)
                flash("Stock update canceled.", "info")
                return redirect(url_for("admin_stock_management"))
    
    return render_template("admin_stock_management.html")

@app.route('/admin_market_management', methods=["GET", "POST"])
@login_required
def admin_market_management():
    if current_user.role != "admin":
        flash("Access denied.", "danger")
        return redirect(url_for("login"))

    show_confirmation = False
    pending_open = session.get("pending_open_time")
    pending_close = session.get("pending_close_time")

    if request.method == "POST":
        form_type = request.form.get("form_type")
        action = request.form.get("action")

        # Market Hours Change
        if form_type == "hours":
            if action == "save_hours":
                open_time = request.form.get("open_time")
                close_time = request.form.get("close_time")
                if not open_time or not close_time:
                    flash("Both open and close times are required.", "danger")
                else:
                    session["pending_open_time"] = open_time
                    session["pending_close_time"] = close_time
                    flash(f"Are you sure you want to set market hours to {open_time} - {close_time}?", "warning")
                    show_confirmation = True

            elif action == "confirm":
                open_time = session.pop("pending_open_time", None)
                close_time = session.pop("pending_close_time", None)
                if open_time and close_time:
                    open_dt = datetime.strptime(open_time, "%H:%M").time()
                    close_dt = datetime.strptime(close_time, "%H:%M").time()
                    market_hours = MarketHours.query.first()
                    if not market_hours:
                        market_hours = MarketHours()
                        db.session.add(market_hours)
                    market_hours.market_open = open_time
                    market_hours.market_close = close_time
                    market_hours.market_open_time = open_dt
                    market_hours.market_close_time = close_dt
                    db.session.commit()
                    session["market_open"] = open_time
                    session["market_close"] = close_time
                    flash("Market hours updated successfully!", "success")
                else:
                    flash("No pending update found.", "danger")
            elif action == "cancel":
                session.pop("pending_open_time", None)
                session.pop("pending_close_time", None)
                flash("Market hour update canceled.", "info")
        
        # Add a Holiday 
        elif form_type == "add_holiday":
            if action == "save_holiday":
                # Get the holiday date as a string directly from the form
                holiday_date_str = request.form.get("holiday_date")
                description = request.form.get("description")
                # You can perform a quick check on the string format if needed.
                try:
                    # Validate the format; this will raise an exception if the format is incorrect.
                    datetime.strptime(holiday_date_str, "%Y-%m-%d")
                    # Store the date string in session (as is)
                    session["pending_holiday_date"] = holiday_date_str
                    session["pending_holiday_description"] = description
                    flash(f"Are you sure you want to add a holiday on {holiday_date_str}?", "warning")
                except Exception as e:
                    flash("Invalid date format. Please use YYYY-MM-DD.", "danger")
                return redirect(url_for("admin_market_management"))
            elif action == "confirm_add_holiday":
                pending_date_str = session.pop("pending_holiday_date", None)
                pending_desc = session.pop("pending_holiday_description", "")
                if pending_date_str:
                    try:
                        # Convert the string to a date object
                        pending_date = datetime.strptime(pending_date_str, "%Y-%m-%d").date()
                        if MarketHoliday.query.filter_by(holiday_date=pending_date).first():
                            flash("A holiday for that date already exists.", "danger")
                        else:
                            new_holiday = MarketHoliday(holiday_date=pending_date, description=pending_desc)
                            db.session.add(new_holiday)
                            db.session.commit()
                            flash("Holiday added successfully.", "success")
                    except Exception as e:
                        flash("Error adding holiday.", "danger")
                else:
                    flash("No pending holiday to add.", "danger")
                return redirect(url_for("admin_market_management"))
            elif action == "cancel_add_holiday":
                session.pop("pending_holiday_date", None)
                session.pop("pending_holiday_description", None)
                flash("Holiday addition canceled.", "info")
                return redirect(url_for("admin_market_management"))
                
        # Delete a Holiday 
        elif form_type == "delete_holiday":
            holiday_id = request.form.get("holiday_id")
            holiday = MarketHoliday.query.get(holiday_id)
            if holiday:
                db.session.delete(holiday)
                db.session.commit()
                flash("Holiday deleted successfully.", "success")
            else:
                flash("Holiday not found.", "danger")
        
        return redirect(url_for("admin_market_management"))

    market_hours = MarketHours.query.first()
    open_time = market_hours.market_open if market_hours else ""
    close_time = market_hours.market_close if market_hours else ""
    holidays = MarketHoliday.query.order_by(MarketHoliday.holiday_date.asc()).all()
    
    return render_template("admin_market_management.html", 
                           open_time=open_time, 
                           close_time=close_time,
                           show_confirmation=show_confirmation,
                           pending_open=pending_open,
                           pending_close=pending_close,
                           holidays=holidays)

#Ending block

if __name__ == '__main__':
    randomizer()
    app.run(debug=True)