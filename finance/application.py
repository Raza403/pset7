from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from passlib.apps import custom_app_context as pwd_context
from tempfile import gettempdir
from collections import defaultdict

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
app.config["SESSION_FILE_DIR"] = gettempdir()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

@app.route("/")
@login_required
def index():
    #Remember id
    ide = session["user_id"]
    #Take all information from users data table, used for determining cash of user.
    row = db.execute ("select * from users where id = :ii" , ii = ide)
    #take info about sahres user has bought
    symb = db.execute("SELECT symbol, price, SUM(shares) as total_shares FROM portfolio WHERE id = :ii GROUP BY symbol ORDER BY symbol",ii=ide)
    #if user has not bought any sahres then display noshare html file.
    if not symb:
    #Return user a message in html and his cash holdings.
        return render_template ("noshares.html",cash = row[0]["cash"])
    else:
        total = 0
        #Iterrate over each element in symb
        for share in symb:
            #Get symbol of each element
            symbol = share ["symbol"]
            #Lookup current price of that specific symbol/sahre
            quote = lookup (symbol)
            #save each current price
            share["quoteprice"] = quote["price"]
            #Total equels fresh quote price of  each stock * sum of shares of each stock
            total += quote["price"] * share ["total_shares"]
        #grand is equel to total + the cash user has in his account
        grand = total + row[0]["cash"]    
        #render values    
        return render_template ("index.html", symbol = symb,cash = row[0]["cash"],gtotal = grand)
            
            
@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock."""
    if request.method == "POST":
        #take symbol from user
        symbl = request.form.get("symbol")
        if not symbl:
            return apology ("Must enter the symbol")
        
        while True:
            #Number of shares to buy
            num = request.form.get("number")
            
            try:
                number = float (num)
            except ValueError:
                return apology ("Please enter valid number of stocks to buy")
                continue
            else:
                break
        if number is None or number == '' or number < 1:
            return apology ("Please enter valid number of stocks to buy")
    
           
        #Lookup and save dict in quoted    
        quoted = lookup(symbl)
        #If symbol is invalid return apology
        if not quoted:
            return apology ("Invalid stock")
        else:
            #qtd saves price of share
            qtd = quoted["price"]
            #price of single share * Number of sahres required to buy
            prc = float(qtd) * number
            #remember session id
            ide = session["user_id"]
           
            csh = db.execute("SELECT * FROM users WHERE id = :ide", ide = ide)
            #Only go forward if user have enough
            if prc <= csh[0]["cash"]:
                db.execute("INSERT INTO portfolio (id, symbol,price,shares,action,dtime) VALUES (:ide, :symbol, :price, :shares,'Buy', DateTime('now'))", ide = ide,symbol = symbl, price = prc, shares = number)
                db.execute("UPDATE users SET cash = :cash WHERE id = :ide",cash = csh[0]["cash"] - prc, ide = ide)
                return redirect(url_for("index"))
            else:
                return apology ("You don't have enough cash to buy these stocks")
    else:
        return render_template("buy.html")

@app.route("/history")
@login_required
def history():
    """Show history of transactions."""
    row = db.execute("SELECT * FROM users WHERE id = :ide", ide = session["user_id"])
    #Select all from portfolio
    symb = db.execute("SELECT * FROM portfolio WHERE id = :ide",ide = session["user_id"])
    #if user has not bought any sahres then display noshare html file.
    if not symb:
    #Return user a message in html and his cash holdings.
        return render_template ("noshares.html",cash = row[0]["cash"])
  
    return render_template ("history.html", symbol = symb)

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

@app.route("/quote", methods=["GET","POST"])
@login_required
def quote():
    #Ensure method of access is get
    if request.method == "POST":
        #take symbol from user
        symbl = request.form.get("symbol")
        if not symbl:
            return apology ("Must enter the symbol")
        #Lookup and save dict in quoted    
        quoted = lookup(symbl)
        #If symbol is invalid return apology
        if not quoted:
            return apology ("Invalid stock")
        #render values to quoted.html    
        else:    
        
            return render_template ("quoted.html", **quoted)
    else:
        return render_template("quote.html")

@app.route("/register", methods=["GET","POST"])
def register():
    # forget any user_id
    session.clear()
    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
               # ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")
            
        # ensure password was submitted
        if not request.form.get("password"):
            return apology("must provide password")
        #ensure again password submitted
        if not request.form.get("again_password"):
            return apology("must provide password again")
        #ensure both password match    
        if request.form.get("password") == request.form.get("again_password"):
            #query database for username
            rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))
           #Ensure usename don't exist already
            if  len(rows) == 0:    
                #Encrypt password
                h = pwd_context.encrypt(request.form.get("password"))
                #insert username and password to SQL data base
                key = db.execute("INSERT INTO users (username, hash) VALUES (:username, :hash)", username=request.form.get("username"), hash=h)
                #Remember user id after successful register.
                session["user_id"] = key

                # redirect user to home page
                return redirect(url_for("index"))
                
            else:
                #return apology if username already exist
                return apology("Username already exist")
        else:
            #return apology if both password don't match with each other
            return apology("both password should match")
    #Return to register.html and use post mathod        
    else:
        return render_template("register.html")

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock."""
    if request.method == "POST":
        #Remember id
        ide = session["user_id"]
        #Get the symbol
        sym = request.form.get("symbol")
        if not sym:
            return apology ("Must enter the symbol")
        #Get number of shares
        #take info about sahres user has of that symbol
        sybl = db.execute ("select * from portfolio where id = :ii AND symbol = :sym" , ii = ide,sym = sym)
        #if user has not bought any sahres
        if not sybl:
        #Go back to index page.
            return redirect(url_for("index"))
        while True:
            num = request.form.get("number")
            
            try:
                
                numb = float (num)
            except ValueError:
                return apology ("Please enter valid number of stocks to sell")
                continue
            else:
                break
        if numb is None or numb == '' or numb < 1 or numb > sybl[0]["shares"]:
            return apology ("Please enter valid number of stocks to sell")
    
        #Take all info about user for cash
        row = db.execute ("select * from users where id = :ii" , ii = ide)
        
        
        #Lookup and save dict in quoted    
        quoted = lookup(sym)
        #If symbol is invalid return apology
        if not quoted:
            return apology ("Invalid stock")
        else:
            #Take price from dict quoted
            qtd = quoted["price"]
            #Multiply current price with number of shares to determine total value of shares sold
            prc = float(qtd)*numb
            #Add current price of the shares to user cash
            db.execute("UPDATE users SET cash = :cash WHERE id = :ide",cash = row[0]["cash"] + prc, ide = ide)
            #Make a negative sale in the portfolio
            db.execute("INSERT INTO portfolio (id, symbol,price,shares,action,dtime) VALUES (:ide, :symbol, :price, :shares,'Sell', DateTime('now'))", ide = ide,symbol = sym, price = prc, shares = -numb)
            return redirect(url_for("index"))
    else:
        return render_template("sell.html")
        
    
@app.route("/addcash", methods=["GET", "POST"])
@login_required
def addcash():
    #For personal touch add cash to user
    if request.method == "POST":
        #Take amount to be added
        while True:
            num = request.form.get("amount")
            try:
                numb = int (num)
            except ValueError:
                return apology ("Please enter valid amount to add")
                continue
            else:
                break
        if numb is None or numb == '' or numb < 1:
            return apology ("Please enter valid amount")
        else:
            #Take user cash
            row = db.execute ("select cash from users where id = :ii" , ii = session["user_id"])
            #Now add the amount to users data base.
            db.execute("UPDATE users SET cash = :cash WHERE id = :ide",cash = row[0]["cash"] + numb, ide = session["user_id"])
        return redirect(url_for("index"))    
            
    else:
        #This programe is taking me straight here.
        return render_template("addcash.html")