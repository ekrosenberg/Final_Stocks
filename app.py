#Initial imports

from flask import Flask, render_template
from flask_bootstrap import Bootstrap5

app = Flask(__name__)
bootstrap = Bootstrap5(app)

#Shared login HTML pages between users and admins

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/')
def base():
    return render_template('base.html')

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

#Ending block

if __name__ == '__main__':
    app.run(debug=True)
