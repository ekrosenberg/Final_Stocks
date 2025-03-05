#Initial imports

from flask import Flask, render_template
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask import request
from flask import redirect, url_for, flash

app = Flask(__name__)
bootstrap = Bootstrap5(app)

# config for db for users
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:password@localhost/flask_project' # make sure to put your own sql database logins
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key'

# extensions for the database and user system
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)

# user model creation for db and login
class Users(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
    role = db.Column(db.String(50), default="user", nullable=False)  # "user" only, manually created "admin" accounts
    portfolio = db.relationship('Portfolio', backref='user', lazy=True)

# stock model creation for db
class Stocks(db.Model):
    __tablename__ = 'stocks'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    ticker_symbol = db.Column(db.String(10), unique=True, nullable=False)
    price = db.Column(db.Numeric(10,2), nullable=False)
    portfolio = db.relationship("Portfolio", back_populates="stock")
    
# portfolio model creation for db
class Portfolio(db.Model):
    __tablename__ = 'portfolio'
    portfolio_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # Ensure Foreign Key Exists
    stock_id = db.Column(db.Integer, db.ForeignKey('stocks.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    purchase_price = db.Column(db.Numeric(10,2), nullable=False)
    current_price = db.Column(db.Numeric(10,2), nullable=False)
    stock = db.relationship('Stocks', back_populates='portfolio')

# creates table for the db
with app.app_context():
    db.create_all()

# user loader to retrieve id numbers
@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))

#Shared login HTML pages between users and admins

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

@app.route('/')
def home():
    return render_template("login.html")

@app.route('/sign_up', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        user = Users(
            username=request.form.get("username"),
            password=request.form.get("password"),  # password unhashed for now, as still adjusting settings and code
            role="user"  # user is default
        )
        db.session.add(user)
        db.session.commit()
        return redirect(url_for("login"))
    return render_template("sign_up.html")

# logout route added
@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for("login"))

#User-exclusive app route pages

@app.route('/user_dashboard', methods=["GET", "POST"])
@login_required
def user_dashboard():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "buy":
            stock_symbol = request.form.get("stockSymbol")
            quantity = request.form.get("quantity")
            flash(f"Stock {stock_symbol} bought successfully")
        elif action == "sell":
            stock_symbol = request.form.get("stockSymbol")
            quantity = request.form.get("quantity")
            flash(f"Stock {stock_symbol} sold successfully")
    else:
        flash("Invalid action", "error")
    return render_template('user_dashboard.html')

@app.route('/user_portfolio')
@login_required
def user_portfolio():
    return render_template('user_portfolio.html')

#Admin-exclusive app route pages

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    return render_template('admin_dashboard.html')

@app.route('/admin_stock_management')
@login_required
def admin_stock_management():
    return render_template('admin_stock_management.html')

#Buy-sell stock app route pages

@app.route('/buy_stock')
@login_required
def buy_stock():
    return render_template('buy_stock.html')

@app.route('/sell_stock')
@login_required
def sell_stock():
    return render_template('sell_stock.html')

#Ending block

if __name__ == '__main__':
    app.run(debug=True)
