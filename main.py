from flask import Flask, render_template, request, make_response, url_for
from sqla_wrapper import SQLAlchemy
from sqlalchemy import ForeignKey
import uuid
from werkzeug.utils import redirect
import requests
from sqlalchemy.orm import relationship

app = Flask(__name__)

db = SQLAlchemy("sqlite:///db.sqlite")


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True)
    email = db.Column(db.String, unique=True)
    password = db.Column(db.String, unique=False)


class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, ForeignKey("users.id"), nullable=False)
    sender = relationship("User", foreign_keys='Message.sender_id')
    receiver_id = db.Column(db.Integer, ForeignKey("users.id"), nullable=False)
    receiver = relationship("User", foreign_keys='Message.receiver_id')
    message = db.Column(db.String, unique=False)


class Sessions(db.Model):
    __tablename__ = 'sessions'
    id = db.Column(db.Integer, primary_key=True)
    username_id = db.Column(db.Integer, ForeignKey("users.id"), nullable=False)
    session_token = db.Column(db.String)


db.create_all()


@app.route("/")
def index():
    session_token = request.cookies.get("session_token")

    if session_token:
        session = db.query(Sessions).filter_by(session_token=session_token).first()
        user = db.query(User).filter_by(id=session.username_id).first()
    else:
        user = None

    return render_template("index.html", user=user)


@app.route("/weather_page", methods=["GET", "POST"])
def weather_page():
    if request.method == "GET":
        return render_template("weather_page.html")

    elif request.method == "POST":
        city = request.form.get("city")
        unit = "metric"
        api_key = "fb403b0a2674cb1dd7e610a68ea73b77"

        url = "https://api.openweathermap.org/data/2.5/weather?q={0}&units={1}&appid={2}".format(city, unit, api_key)
        data = requests.get(url=url)
        if data.json()['cod'] == 200:
            return render_template("weather_page.html", data=data.json())
        else:
            return 'City does not exist'


@app.route("/sent_messages")
def sent_messages():
    session_token = request.cookies.get("session_token")
    session = db.query(Sessions).filter_by(session_token=session_token).first()
    sent_message = db.query(Message).filter_by(sender_id=session.username_id)
    user = db.query(User).filter_by(id=session.username_id).first()
    return render_template("sent_messages.html", sent_message=sent_message, user=user)


@app.route("/received_messages")
def received_messages():
    session_token = request.cookies.get("session_token")
    session = db.query(Sessions).filter_by(session_token=session_token).first()
    received_message = db.query(Message).filter_by(receiver_id=session.username_id)
    user = db.query(User).filter_by(id=session.username_id).first()
    return render_template("received_messages.html", received_message=received_message, user=user)


@app.route("/registration", methods=["GET", "POST"])
def registration():
    if request.method == "GET":
        return render_template("registration.html")
    elif request.method == "POST":
        contact_username = request.form.get("contact-username")
        contact_email = request.form.get("contact-email")
        contact_password = request.form.get("contact-password")
        user_username = db.query(User).filter_by(username=contact_username).first()
        user_email = db.query(User).filter_by(email=contact_email).first()

        if contact_username == '' or contact_email == '' or contact_password == '':
            return 'You must fill out all the boxes'
        elif user_username is not None:
            return 'Username already registered'
        elif user_email is not None:
            return 'Email already used'
        else:
            user = User(username=contact_username, email=contact_email, password=contact_password)
            user.save()
            session_token = str(uuid.uuid4())
            session = Sessions()
            session.username_id = user.id
            session.session_token = session_token
            session.save()

            response = make_response(redirect(url_for('index')))
            response.set_cookie("session_token", session_token, httponly=True, samesite='Strict')
            return response


@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("user-name")
    password = request.form.get("user-password")

    user = db.query(User).filter_by(username=username).first()

    if not user:
        return "User not yet in the system. Register first"

    if password != user.password:
        return "WRONG PASSWORD! Go back and try again."

    elif password == user.password:
        # create a random session token for this user
        session_token = str(uuid.uuid4())
        session = Sessions()
        session.username_id = user.id
        session.session_token = session_token
        session.save()

        response = make_response(redirect(url_for('index', user=user)))
        response.set_cookie("session_token", session_token, httponly=True, samesite='Strict')

        return response


@app.route("/message", methods=["POST"])
def message():
    message_sent = request.form.get("message")
    receiver1 = request.form.get("receiver")
    session_token = request.cookies.get("session_token")
    session = db.query(Sessions).filter_by(session_token=session_token).first()
    receiver = db.query(User).filter_by(username=receiver1).first()

    if not receiver:
        return "Receiver not yet in the system. You can sent message only to register users."

    if message_sent == '':
        return "Empty space is not a valid message"

    post_message = Message()
    post_message.sender_id = session.username_id
    post_message.receiver_id = receiver.id
    post_message.message = message_sent
    post_message.save()

    user = db.query(User).filter_by(id=session.username_id).first()

    return render_template("index.html", user=user)


@app.route("/logout")
def logout():

    response = make_response(redirect(url_for('index')))
    response.delete_cookie("session_token", "/", secure=False, httponly=True, samesite='Strict')
    return response


if __name__ == '__main__':
    app.run(use_reloader=True)
