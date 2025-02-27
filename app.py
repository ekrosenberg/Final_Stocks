#Initial imports

from flask import Flask, render_template
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

app = Flask(__name__)
bootstrap = Bootstrap5(app)

# config for db for users
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:1010@localhost/flask_project' # make sure to put your own sql database logins
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

# creates table for the db
with app.app_context():
    db.create_all()

# user loader to retrieve id numbers
@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))

#Shared login HTML pages between users and admins

@app.route('/login')
def login():
    if request.method == "POST":
        user = Users.query.filter_by(username=request.form.get("username")).first()
        if user and user.password == request.form.get("password"):
            login_user(user)
            return redirect(url_for("login"))
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

@app.route('/user_dashboard')
def user_dashboard():
    return render_template('user_dashboard.html')

@app.route('/user_stock_management')
def user_stock_management():
    return render_template('user_stock_management.html')

#Admin-exclusive app route pages

@app.route('/admin_dashboard')
def admin_dashboard():
    return render_template('admin_dashboard.html')

@app.route('/admin_stock_management')
def admin_stock_management():
    return render_template('admin_stock_management.html')

#Buy-sell stock app route pages

@app.route('/buy_stock')
def buy_stock():
    return render_template('buy_stock.html')

@app.route('/sell_stock')
def sell_stock():
    return render_template('sell_stock.html')

#Ending block

if __name__ == '__main__':
    app.run(debug=True)
