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
from datetime import datetime
import time

app = Flask(__name__)
bootstrap = Bootstrap5(app)

# Database Config
app.config['SECRET_KEY'] = 'your-secret-key'

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:password@localhost/flask_project' # Edit SQL login for local machine
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
    
# Portfolio model creation for database

class Portfolio(db.Model):
    __tablename__ = 'portfolio'
    portfolio_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    stock_id = db.Column(db.Integer, db.ForeignKey('stocks.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    purchase_price = db.Column(db.Numeric(10,2), nullable=False)
    current_price = db.Column(db.Numeric(10,2), nullable=False)

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

#Creates a model for the balance
class Balance(db.Model):
    __tablename__ = 'balance'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    balance = db.Column(db.Numeric(10,2), nullable=False, default=0.00)

    user = db.relationship('Users', backref=db.backref('balance', uselist=False))

#Price Random Generator / Auto-Triggers on Startup

def randomizer():
    stocks = Stocks.query.all()
    for stock in stocks:
        stock.price += Decimal(random.uniform(-250, 250))
    db.session.commit()

# Creates table for the database

with app.app_context():
    db.create_all()
    randomizer()  

# User loader to retrieve id numbers

@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))

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
    flash("The stock market has been updated!", "info")
    return render_template('user_home.html', stocks=stocks)

@app.route('/user_portfolio')
@login_required
def user_portfolio():
    #The users transactions are retrieved
    transactions = Transactions.query.filter_by(user_id=current_user.id).all()

    #The transactions are sent to the template
    return render_template('user_portfolio.html', user=current_user, transactions=transactions)


@app.route('/user_trades', methods=["GET", "POST"])
@login_required
def user_trades():
    if request.method == "POST":

        action = request.form.get("action")
        if action == "buy":
            stock_symbol = request.form.get("buyStockSymbol", "").strip().upper()
            quantity = request.form.get("buyQuantity", "").strip()
        elif action == "sell":
            stock_symbol = request.form.get("sellStockSymbol", "").strip().upper()
            quantity = request.form.get("sellQuantity", "").strip()
        else:
            stock_symbol = ""
            quantity = ""
        
        if not stock_symbol:
            flash(f"Stock symbol is required. Received: '{stock_symbol}'", "danger")
            return redirect(url_for("user_trades"))

        if action == "buy":
            quantity = request.form.get("buyQuantity", "").strip()
        elif action == "sell":
            quantity = request.form.get("sellQuantity", "").strip()
        else:
            quantity = ""

        if not quantity.isdigit():
            flash("Invalid quantity. Please enter a valid number.", "danger")
            return redirect(url_for("user_trades"))

        quantity = int(quantity)
        stock = Stocks.query.filter_by(ticker_symbol=stock_symbol).first()

        if not stock:
            flash("Stock not found. Please enter a valid stock symbol.", "danger")
            return redirect(url_for("user_trades"))

        total_price = stock.price * quantity

        if action == "buy":

            session["pending_transaction"] = {
                "action": "buy",
                "stock_symbol": stock_symbol,
                "quantity": quantity,
                "total_price": float(total_price)
            }

            session.modified = True

            flash(
                f"Are you sure you want to buy {quantity} shares of {stock_symbol} for ${total_price:.2f}?",
                "warning"
            )
            return redirect(url_for("user_trades"))

        elif action == "confirm_purchase":
            transaction = session.get("pending_transaction")

            if not transaction:
                flash("Transaction not found. Please try again.", "danger")
                return redirect(url_for("user_trades"))

            stock_symbol = transaction.get("stock_symbol")
            quantity = transaction.get("quantity")
            total_price = transaction.get("total_price")

            stock = Stocks.query.filter_by(ticker_symbol=stock_symbol).first()
            if not stock:
                flash("Stock no longer available.", "danger")
                return redirect(url_for("user_trades"))

            user_balance = Balance.query.filter_by(user_id=current_user.id).first()

            if user_balance.balance >= total_price:
                user_balance.balance -= total_price

                new_transaction = Transactions(
                    user_id=current_user.id,
                    stock_symbol=stock_symbol,
                    transaction_type="buy",
                    quantity=quantity,
                    price=stock.price,
                    total_amount=total_price
                )
                db.session.add(new_transaction)
                db.session.commit()

                flash(f"Successfully bought {quantity} shares of {stock_symbol}!", "success")
            else:
                flash("Insufficient funds to complete the purchase.", "danger")

            session.pop("pending_transaction", None)
            return redirect(url_for("user_trades"))

        elif action == "cancel_purchase":
            session.pop("pending_transaction", None)
            flash("Purchase canceled.", "info")
            return redirect(url_for("user_trades"))

        elif action == "sell":
            user_stock = Portfolio.query.filter_by(user_id=current_user.id, stock_id=stock.id).first()

            if not user_stock or user_stock.quantity < quantity:
                flash("You do not have enough shares to sell.", "danger")
                return redirect(url_for("user_trades"))

            #Stores pending sale transactions
            session["pending_transaction"] = {
                "action": "sell",
                "stock_symbol": stock_symbol,
                "quantity": quantity,
                "total_price": float(total_price)
            }

            session.modified = True

            flash(f"Are you sure you want to sell {quantity} shares of {stock_symbol} for ${total_price:.2f}?", "warning")
            return redirect(url_for("user_trades"))

        #Sell action is confirmed
        elif action == "confirm_sell":
            transaction = session.get("pending_transaction")

            if not transaction:
                flash("Transaction not found. Please try again.", "danger")
                return redirect(url_for("user_trades"))

            stock_symbol = transaction.get("stock_symbol")
            quantity = transaction.get("quantity")
            total_price = transaction.get("total_price")

            stock = Stocks.query.filter_by(ticker_symbol=stock_symbol).first()
            if not stock:
                flash("Stock no longer available.", "danger")
                return redirect(url_for("user_trades"))

            user_stock = Portfolio.query.filter_by(user_id=current_user.id, stock_id=stock.id).first()
            if not user_stock or user_stock.quantity < quantity:
                flash("You do not have enough shares to sell.", "danger")
                return redirect(url_for("user_trades"))

            #Shares are deducted from the user
            user_stock.quantity -= quantity
            if user_stock.quantity == 0:
                db.session.delete(user_stock)

            #Checks user has balance
            user_balance = Balance.query.filter_by(user_id=current_user.id).first()
            if not user_balance:
                user_balance = Balance(user_id=current_user.id, balance=0.00)
                db.session.add(user_balance)
                db.session.commit()

            #Sold share money is added to the account
            user_balance.balance += total_price

            #Records the transactions
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

        #Sell action is cancelled by user
        elif action == "cancel_sell":
            session.pop("pending_transaction", None)
            flash("Sell transaction canceled.", "info")
            return redirect(url_for("user_trades"))

    stocks = Stocks.query.all()
    return render_template("user_trades.html", stocks=stocks)

@app.route('/user_transactions')
@login_required
def user_transactions():
    transactions = Transactions.query.filter_by(user_id=current_user.id).all()
    return render_template('user_transactions.html', transactions=transactions)

#Admin exclusive HTML pages

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    #Add a conditional block that checks if admin role here to prevent security bug
    return render_template('admin_dashboard.html')

@app.route('/admin_stock_management')
@login_required
def admin_stock_management():
    #Add a conditional block that checks if admin role here to prevent security bug
    return render_template('admin_stock_management.html')

#Ending block

if __name__ == '__main__':
    app.run(debug=True)