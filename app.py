# Python Imports

from flask import Flask, render_template
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask import request
from flask import redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
import random, math

app = Flask(__name__)
bootstrap = Bootstrap5(app)

# Database Config

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:1010@localhost/flask_project' # Edit SQL login for local machine
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key'
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
    portfolio = db.relationship("Portfolio", back_populates="stock")
    
# Portfolio model creation for database

class Portfolio(db.Model):
    __tablename__ = 'portfolio'
    portfolio_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    stock_id = db.Column(db.Integer, db.ForeignKey('stocks.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    purchase_price = db.Column(db.Numeric(10,2), nullable=False)
    current_price = db.Column(db.Numeric(10,2), nullable=False)
    stock = db.relationship('Stocks', back_populates='portfolio')

# Creates table for the database

with app.app_context():
    db.create_all()

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
        user = Users.query.filter_by(username=request.form.get("username")).first()
        if user and user.password == request.form.get("password"):
            login_user(user)
            if user.role == "admin":
                return redirect(url_for("admin_dashboard"))
            else:
                return redirect(url_for("user_dashboard"))
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

@app.route('/user_dashboard', methods=["GET", "POST"])
@login_required
def user_dashboard():
    if request.method == "POST":
        action = request.form.get("action")
        stock_symbol = request.form.get("stockSymbol")
        quantity = int(request.form.get("quantity"))
        stock = Stocks.query.filter_by(ticker_symbol=stock_symbol).first()
        portfolio_entry = Portfolio.query.filter_by(user_id=current_user.id, stock_id=stock.id).first()
        if action == "buy":
            if portfolio_entry:
                portfolio_entry.quantity += quantity
                portfolio_entry.purchase_price = stock.price
            else:
                new_entry = Portfolio(
                    user_id=current_user.id,
                    stock_id=stock.id,
                    quantity=quantity,
                    purchase_price=stock.price,
                    current_price=stock.price
                )
                db.session.add(new_entry)
            flash(f"Stock {stock_symbol} bought successfully")
        elif action == "sell":
            if portfolio_entry and portfolio_entry.quantity >= quantity:
                portfolio_entry.quantity -= quantity
                if portfolio_entry.quantity == 0:
                    db.session.delete(portfolio_entry)
                flash(f"Stock {stock_symbol} sold successfully", "success")
            else:
                flash("Not enough shares to sell", "error")
        db.session.commit()
    else:
        flash("Invalid action", "error")
    return render_template('user_dashboard.html')

@app.route('/user_portfolio')
@login_required
def user_portfolio():
    return render_template('user_portfolio.html')

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
