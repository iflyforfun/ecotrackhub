from datetime import datetime
import os
import random as ran
from flask import Flask, redirect, render_template, request, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, LoginManager, login_user, login_required, current_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
import plotly.express as px

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SECRET_KEY'] = os.environ['secret_key']
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(
    basedir, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

db = SQLAlchemy(app)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200))  # Store hashed passwords as strings
    xp = db.Column(db.Integer,default=0)
    def __repr__(self):
        return f'<User {self.name}>'


class Entry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), nullable=False)
    public_transport_hours = db.Column(db.Integer)
    energy_consumption = db.Column(db.Integer)
    waste_recycled = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.now())


#with app.app_context():
    #db.drop_all()
    #db.create_all()


def get_entries(user):
    try:
        if user.is_authenticated:
            entries = Entry.query.filter_by(email=user.email).all()
            serialized_entries = []
            for entry in entries:
                entry_data = {
                    "id": entry.id,
                    "email": entry.email,
                    "public_transport_hours": entry.public_transport_hours,
                    "energy_consumption": entry.energy_consumption,
                    "waste_recycled": entry.waste_recycled,
                    "created_at": entry.created_at
                }
                serialized_entries.append(entry_data)
            return serialized_entries
        else:
            return False
    except Exception as e:
        return False
  

def calculate_totals_and_averages(entries):
    totals = [0, 0, 0]
    entries_amt = len(entries)
  
    for entry in entries:
        totals[0] += entry["public_transport_hours"]
        totals[1] += entry["energy_consumption"]
        totals[2] += entry["waste_recycled"]
    
    averages = [total / entries_amt for total in totals]
  
    return totals, averages


def calculate_latest_values(entries):
    if entries != []:
        return [
            entries[-1]["public_transport_hours"], entries[-1]["energy_consumption"],
            entries[-1]["waste_recycled"]
        ]
    else:
        return [0,0,0]


def calculate_overall_values(entries):
    values = [0, 0, 0, 0]
  
    for entry in entries:
        values[0] += entry["public_transport_hours"]
        values[1] += entry["energy_consumption"]
        values[2] += entry["waste_recycled"]
        values[3] += 1
  
    return values


def calculate_xp(public_transport_hours,energy_consumption,waste_recycled,user):
    xp_to_add = public_transport_hours + round(energy_consumption/10 + waste_recycled/2)
    user.xp += xp_to_add
    return user.xp

def get_xp(user):
    return (user.xp-(user.xp%100))/100,user.xp%100
    

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
def index():
    return render_template('index.html')


@app.route("/ourmission")
def ourmission():
    return render_template("ourmission.html")


@app.route("/learnmore")
def learnmore():
    return render_template("learnmore.html")


@app.route("/signup")
def signup():
    return render_template("signup.html")


@app.route("/signup", methods=['POST'])
def signup_post():
    email = request.form['email']
    name = request.form['name']
    password = request.form['password']
    cfrmpassword = request.form['cfrmpassword']
    if cfrmpassword != password:
        flash("Passwords do not match")
        return redirect(url_for('signup'))
    user = User.query.filter_by(email=email).first()
  
    if user:
        flash('Email address already exists')
        return redirect(url_for('signup'))
  
    new_user = User(email=email,
                    name=name,
                    password=generate_password_hash(password, method='pbkdf2'))
  
    db.session.add(new_user)
    db.session.commit()
    return redirect(url_for("login"))
  

@app.route("/profile/edit-profile")
@login_required
def edit_profile():
    return render_template("editprofile.html",
                           name=current_user.name,
                           email=current_user.email)
  

@app.route("/profile/edit-profile", methods=['POST'])
def edit_profile_post():
    email = request.form['email']
    name = request.form['name']
    password = request.form['password']
    cfrmpassword = request.form['cfrmpassword']
  
    if current_user.is_authenticated:
        current_user.email = email
        current_user.name = name
        if password and cfrmpassword == password:
            current_user.password = generate_password_hash(password, method='pbkdf2')
        db.session.commit()
        flash("Profile updated successfully")
        return redirect(url_for("profile"))
    else:
        flash("User not authenticated")
        return redirect(url_for("login.html"))


@app.route("/profile/calculator")
@login_required
def calculator():
    return render_template("calculator.html")


@app.route('/profile/calculator/results')
@login_required
def footprintresults():
    carbon_footprint = request.args.get('carbonFootprint',
                                        default='Not available')
    try:
        int_carbon_footprint = round(float(carbon_footprint))
    except TypeError:
        return render_template('calculator.html')
    return render_template('footprintresults.html',
                           carbon_footprint=int_carbon_footprint)


@app.route("/profile")
@login_required
def profile():
    sustainable_tips = [
        "Turn off lights and appliances when not in use.",
        "Use energy-efficient LED bulbs.",
        "Unplug chargers and electronics when not in use.",
        "Switch to renewable energy sources like solar or wind power.",
        "Set thermostat a few degrees lower in winter and higher in summer.",
        "Fix leaks in faucets and pipes to conserve water.",
        "Collect rainwater for watering plants.",
        "Reduce, reuse, and recycle to minimize waste.",
        "Bring reusable bags when shopping.",
        "Compost organic waste to reduce landfill.",
        "Choose products with minimal packaging.",
        "Use public transportation, carpool, or bike.",
        "Opt for electronic communication to reduce paper usage.",
        "Choose energy-efficient appliances.",
        "Support local and sustainable businesses.",
        "Educate yourself and others about sustainable practices.",
        "Conserve water by taking shorter showers.",
        "Plant trees and participate in clean-up events.",
        "Turn off the tap while brushing your teeth.",
        "Invest in a reusable water bottle.",
    ]
    entries = get_entries(current_user)
    values = calculate_overall_values(entries)
    latest = calculate_latest_values(entries)
    level,xp = get_xp(current_user)
    for i in latest:
        values.append(i)  
    return render_template("profile.html",
                           name=current_user.name,
                           tip=ran.choice(sustainable_tips),
                           values=values,
                           level=int(level),
                           xp=int(xp))

@app.route("/profilev2")
@login_required
def profile_two():
    sustainable_tips = [
        "Turn off lights and appliances when not in use.",
        "Use energy-efficient LED bulbs.",
        "Unplug chargers and electronics when not in use.",
        "Switch to renewable energy sources like solar or wind power.",
        "Set thermostat a few degrees lower in winter and higher in summer.",
        "Fix leaks in faucets and pipes to conserve water.",
        "Collect rainwater for watering plants.",
        "Reduce, reuse, and recycle to minimize waste.",
        "Bring reusable bags when shopping.",
        "Compost organic waste to reduce landfill.",
        "Choose products with minimal packaging.",
        "Use public transportation, carpool, or bike.",
        "Opt for electronic communication to reduce paper usage.",
        "Choose energy-efficient appliances.",
        "Support local and sustainable businesses.",
        "Educate yourself and others about sustainable practices.",
        "Conserve water by taking shorter showers.",
        "Plant trees and participate in clean-up events.",
        "Turn off the tap while brushing your teeth.",
        "Invest in a reusable water bottle.",
    ]
    entries = get_entries(current_user)
    values = calculate_overall_values(entries)
    latest = calculate_latest_values(entries)
    level,xp = get_xp(current_user)
    for i in latest:
        values.append(i)  
    return render_template("profilev2.html",
                           name=current_user.name,
                           tip=ran.choice(sustainable_tips),
                           values=values,
                           level=int(level),
                           xp=int(xp))


@app.route("/login")
def login():
    return render_template("login.html")


@app.route("/login", methods=['POST'])
def login_post():
    email = request.form['email']
    password = request.form['password']
    remember = bool(request.form.get('remember'))
    user = User.query.filter_by(email=email).first()
  
    if not user or not check_password_hash(user.password, password):
        flash('Please check your login details and try again.')
        return redirect(url_for('login'))
  
    login_user(user, remember=remember)
    return redirect(url_for("profile"))


@app.route("/profile/habit_tracker")
@login_required
def habittracker():
    entries = get_entries(current_user)
    if not entries:
        values = [0, 0, 0, 0]
    else:
        values = [0, 0, 0, 0]
        for i in entries:
            values[0] += i["public_transport_hours"]
            values[1] += i["energy_consumption"]
            values[2] += i["waste_recycled"]
            values[3] += 1
    return render_template("habittracker.html", values=values)


@app.route("/profile/habit_tracker", methods=['POST'])
def log_habit():
    if not current_user.is_authenticated:
        flash("You need to be logged in to access this page")
        return render_template("login.html")
    public_transport_hours = int(request.form['public_transport_hours'])
    energy_consumption = int(request.form['energy_consumption'])
    waste_recycled = int(request.form['waste_recycled'])
    if public_transport_hours > 24 or public_transport_hours <= -1:
        flash("Please enter a valid positive time up to 24 hours")
        return redirect(url_for('habittracker'))
    elif energy_consumption > 100 or energy_consumption <= -1:
        flash("Please enter a valid positive value up to 100 kWh")
        return redirect(url_for('habittracker'))
    elif waste_recycled > 1000 or waste_recycled <= -1:
        flash("Please enter a valid positive value up to 1000 kg")
        return redirect(url_for('habittracker'))
    if waste_recycled == 0 and energy_consumption == 0 and public_transport_hours == 0:
        flash("One value must be more than 0")
        return redirect(url_for('habittracker'))
    user_email = current_user.email
    entry = Entry(email=user_email,
                  public_transport_hours=public_transport_hours,
                  energy_consumption=energy_consumption,
                  waste_recycled=waste_recycled)
    current_user.xp = calculate_xp(public_transport_hours,energy_consumption,waste_recycled,current_user)
    db.session.add(entry)
    db.session.commit()
    flash('Habits logged successfully')
    return redirect(url_for('profile'))


@app.route("/profile/in-depth")
def indepth():
    user = current_user
    entries = get_entries(user)
  
    data = {
        "Public Transport Time": [],
        "Energy Consumption": [],
        "Waste Recycled": []
    }
    entries_amt = 0
  
    for entry in entries:
        data["Public Transport Time"].append(entry["public_transport_hours"])
        data["Energy Consumption"].append(entry["energy_consumption"])
        data["Waste Recycled"].append(entry["waste_recycled"])
        entries_amt += 1
  
    totals, averages = calculate_totals_and_averages(entries)
    latest = calculate_latest_values(entries)
  
    dataframe = pd.DataFrame(data)
    fig = px.line(dataframe,
                  title="In-Depth Analysis",
                  labels={
                      "index": "Entry",
                      "value": "Amount"
                  })
    graph_json = fig.to_json()
  
    return render_template("indepth.html",
                           graph_json=graph_json,
                           totals=totals,
                           averages=averages,
                           latest=latest)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))
  

if __name__ == "__main__":
    app.run(host="0.0.0.0", port='8080', debug=True)
