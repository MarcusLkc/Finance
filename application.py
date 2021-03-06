from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from passlib.apps import custom_app_context as pwd_context
from tempfile import mkdtemp

from helpers import *

# configure application
app = Flask(__name__)

# ensure responses aren't cached
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

# custom filter
app.jinja_env.filters["usd"] = usd

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

@app.route("/")
@login_required
def index():
    #Update User Stock Prices to match current Yahoo Prices
    
    stocks = db.execute("SELECT * FROM Stocks WHERE id = :id",id=session["user_id"])
    cash = db.execute("SELECT cash FROM users WHERE id = :id",id=session["user_id"])
    total_cash = 0
    
    #Cycle through stocks updating the price per each in database
    for stock in stocks:
        symbol = stock["symbol"]
        shares = stock["shares"]
        stock = lookup(symbol)
        total = shares * stock["price"]
        total_cash += total
        db.execute("UPDATE Stocks SET price=:price, \
                    total=:total WHERE id=:id AND symbol=:symbol", \
                    price=usd(stock["price"]), \
                    total=usd(total), id=session["user_id"], symbol=symbol)

    # Get the user's current cach
    updated_cash = db.execute("SELECT cash FROM users \
                               WHERE id=:id", id=session["user_id"])
    
    # Total Cash combination of all of stocks values and cash on hand by user
    total_cash += updated_cash[0]["cash"]
    return render_template("index.html",stocks=stocks,cash=usd(cash[0]["cash"]),total= usd(total_cash))

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock."""
    if request.method == "POST":
        shares = 0
        
        #check to seee if user is putting the right variables into input fields
        
        if not request.form.get("symbol") or not request.form.get("shares"):
            flash("Please remmember to fill both fields")
            return render_template("buy.html")
        try:
            shares = int(request.form.get("shares"))
            if shares < 0:
                
                return apology("Shares must be a positive Integer")
                
            
        except ValueError:
            
            flash("Shares have to be a numeric value")
            return redirect(url_for("buy.html"))
            
        #lookup that stock's symbol from yahoo and find in database
            
        stock = lookup(request.form.get("symbol"))
        if not stock:
            return apology("Share does not exist")
        cost = stock["price"] * shares
        rows = db.execute("SELECT cash FROM Users WHERE id = :id", id=session["user_id"])
        print(shares)
        if rows[0]["cash"] < cost:
            return apology("You don't have enough money for that =(")
            
            
        #Update User's Cash
        
        db.execute("UPDATE Users SET cash = cash -:cost WHERE id = :id",cost=cost,id=session["user_id"])
        
        #Save purchase into history
        
        db.execute("INSERT INTO History(id,symbol,shares,price) VALUES(:id,:symbol,:shares,:price)",id=session["user_id"],symbol=stock["symbol"],shares=shares,price=usd(stock["price"]))
        
        current_shares = db.execute("SELECT SHARES FROM Stocks WHERE id = :id AND symbol = :symbol",id=session["user_id"],symbol=stock["symbol"])
        
        #If no current shares of that company create a new row in Stocks table for that User
        
        if not current_shares:
            
            db.execute("INSERT INTO Stocks(id,name,symbol,shares,price,total) VALUES(:id,:name,:symbol,:shares,:price,:total)",id=session["user_id"],name=stock["name"],symbol=stock["symbol"],shares=shares,price=usd(stock["price"]),total=usd(shares*stock["price"]))
            
            flash("Successfully bought")
            
            return redirect(url_for("index"))
            
        # if there is shares of that company just increment the current shares
        
        current_shares = current_shares[0]["shares"] + shares
        
        db.execute("UPDATE Stocks SET shares = :shares,price=:price,total=:total WHERE id=:id AND symbol = :symbol",shares=current_shares,price=stock["price"],total=usd(current_shares*stock["price"]),id=session["user_id"],symbol=stock["symbol"])
        
        flash("Sucessfully Added new Shares")
        
        return redirect(url_for("index"))
        
        
        
        
    
    return render_template("buy.html")

@app.route("/history")
@login_required
def history():
    """Show history of transactions."""
    #Grab All the Users History from the Database
    
    History = db.execute("SELECT * FROM History WHERE id = :id ORDER BY TransactionID DESC", id = session["user_id"])
    return render_template("history.html",History=History)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in."""

    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        # query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        # ensure username exists and password is correct
        if len(rows) != 1 or not pwd_context.verify(request.form.get("password"), rows[0]["hash"]):
            return apology("invalid username and/or password")

        # remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # redirect user to home page
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out."""

    # forget any user_id
    session.clear()

    # redirect user to login form
    return redirect(url_for("login"))

@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        if not request.form.get("symbol"):
            
            flash(u'Please Enter a Stock', 'error')
            
            return redirect(url_for("quote"))
        else:
            
            stock = lookup(request.form.get("symbol"))
            
            if not stock:
                flash(u'Please Enter a valid Stock symbol')
                return redirect(url_for("quote"))
            
            return render_template("quoted.html",quoted=stock)
    else:
        
        return render_template("quote.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user."""
    if request.method == "POST":
    
        if not request.form.get("username"):
            return apology("must provide username")
    
            # ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")
        elif not request.form.get("password") == request.form.get("password2"):
            return apology("passwords do not match")
        
        else:
            rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

            # ensure username exists and password is correct
            if len(rows) == 1:
                return apology("Username Already in use")
    
          
            user = db.execute("INSERT INTO users(username,hash) VALUES(:username,:hash)",username=request.form.get("username"),hash=pwd_context.encrypt(request.form.get("password")))
           
            
            # remember which user has logged in
            session["user_id"] = user
                
            
            
            flash(u'You were successfully registered now Get started with stocks')
            return redirect(url_for("index"))
        

    else:
        return render_template("register.html")

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock."""
    
    #Similar to buy
    
    if request.method == "POST":
        shares = 0
        
        if not request.form.get("symbol") or not request.form.get("shares"):
            flash("Please remmember to fill both fields")
            return render_template("buy.html")
        try:
            shares = int(request.form.get("shares"))
            if shares < 0:
                
                return apology("Shares must be a positive Integer")
                
            
        except ValueError:
            
            flash("Shares have to be a numeric value")
            return redirect(url_for("buy.html"))
        stock = lookup(request.form.get("symbol"))
        
        if not stock:
            return apology("Share does not exist")
        cost = stock["price"] * float(shares)
        rows = db.execute("SELECT shares FROM Stocks WHERE id = :id AND symbol = :symbol", id=session["user_id"],symbol=stock["symbol"])
        
        current_cash = db.execute("SELECT cash FROM users WHERE id = :id",id=session["user_id"])
        
        current_cash = current_cash[0]["cash"] + cost
        
        #Users without shares can not sell
        if not rows:
            return apology("You do not have this share")
        
        
        if (rows[0]["shares"] - shares) < 0:
            return apology("You don't have enough of those Shares for that =(")
        
        db.execute("UPDATE Users SET cash = :current_cash WHERE id = :id",current_cash=current_cash,id=session["user_id"])
        
        db.execute("INSERT INTO History(id,symbol,shares,price) VALUES(:id,:symbol,:shares,:price)",id=session["user_id"],symbol=stock["symbol"],shares=-shares,price=usd(stock["price"]))
        
        current_shares = db.execute("SELECT SHARES FROM Stocks WHERE id = :id AND symbol = :symbol",id=session["user_id"],symbol=stock["symbol"])
        current_shares = current_shares[0]["shares"] - shares
        
        
        #If users end up with none of that share delete it from their Stocks
        
        if current_shares == 0:
            
            db.execute("DELETE FROM Stocks WHERE id = :id AND symbol = :symbol",id=session["user_id"],symbol=stock["symbol"])
            
            flash("Successfully SOLD")
            
            return redirect(url_for("index"))
        
        #If shares are above 0 just update the stocks object
        
        db.execute("UPDATE Stocks SET shares = :shares,price=:price,total=:total WHERE id=:id AND symbol = :symbol",shares=current_shares,price=stock["price"],total=usd(current_shares*stock["price"]),id=session["user_id"],symbol=stock["symbol"])
        
        flash("Sucessfully Sold Shares")
        
        return redirect(url_for("index"))
    
    return render_template("sell.html")
        

@app.route("/loan", methods=["GET", "POST"])
@login_required
def loan():
    
    """Get a loan for users to purchase more stocks"""
    
    
    if request.method == "POST":
        loan_amount = 0
        try:
            loan_amount = int(request.form.get("loan"))
            
        except ValueError:
            
            return apology("Loan must be Positive Integers only")
            
        
        if not loan_amount:
            
            return apologu("Please do not leave loan field blank")
        
        elif loan_amount < 0 or loan_amount > 10000:
            
            return apology("Please only use positive loan amounts less than $10,000")
        
        rows = db.execute("UPDATE users SET cash = cash + :loan_amount WHERE id=:id",loan_amount=loan_amount,id=session["user_id"])
        
        flash("Loan Successful")
        
        return redirect(url_for("index"))
        
    
    return render_template("loan.html")
