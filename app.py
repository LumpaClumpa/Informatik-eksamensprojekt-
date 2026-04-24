from flask import Flask, render_template, url_for, redirect, request, session

app = Flask(__name__)

username_lærer = "lærer"
password_lærer = "lærer1234"

username_elev = "elev"
password_elev = "elev1234"


@app.route('/')
def home():
    if not session.get("logged_in"):
        return render_template("home.html", locked=True)
    return render_template("home.html", locked=False)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        username = request.form.get("username").lower()
        password = request.form.get("password")
        
        if username == "elev" and password == "elev1234":
            session["logged_in"] = True
            return redirect(url_for("home"))
        if username == username_lærer and password == password_lærer:
            session["logged_in"] = True
            return redirect(url_for("home"))
        else:
            return render_template("login.html", error="Ikke gyldig login")

    return render_template("login.html")


@app.route('/velkommen-laerer')
def velkommen_lærer():
    return "Velkommen lærer"


@app.route('/velkommen-elev')
def velkommen_elev():
    return "Velkommen elev"


if __name__ == '__main__':
    app.run(debug=True)