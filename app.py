from flask import Flask, render_template
from flask_bootstrap import Bootstrap5

app = Flask(__name__)
bootstrap = Bootstrap5(app)

@app.route('/')
def base():
    return render_template('base.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/stock_management')
def stock_management():
    return render_template('stock_management.html')

if __name__ == '__main__':
    app.run(debug=True)
