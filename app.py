from flask import Flask, redirect, request, session, url_for, render_template, jsonify
import requests
from apscheduler.schedulers.background import BackgroundScheduler
import os

app = Flask(__name__)
app.secret_key = "random_bogus_secret_key"

CLIENT_ID = "paste id here"
CLIENT_SECRET = "paste secret here"
REDIRECT_URI = "http://127.0.0.1:5000/authorize"

egv_data = None
access_token = None

# Function to fetch EGV data
def update_egv_data():
    global access_token
    print("Updating EGVs with access token: ", access_token)
    
    url = "https://sandbox-api.dexcom.com/v3/users/self/egvs"
    query = {
        "startDate": "2024-02-06T09:12:35",
        "endDate": "2024-02-06T09:12:35"
    }
    headers = {"Authorization": f"Bearer {access_token}"}

    try:
        response = requests.get(url, headers=headers, params=query)
        response.raise_for_status()  # Raise an exception for non-200 status codes
        global egv_data
        egv_data = response.json()
        print(egv_data)
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None  # Handle errors gracefully
    
    
def get_bearer_token(auth_code):
    print("GETTING BEARER TOKEN")
    url = "https://sandbox-api.dexcom.com/v2/oauth2/token"

    payload = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }

    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    
    response = requests.post(url, data=payload, headers=headers)

    token = response.json().get("access_token")
    print(token)
    return token

    
scheduler = BackgroundScheduler()
scheduler.add_job(update_egv_data, 'interval', seconds=30)
scheduler.start()

@app.route("/")
def home():
    # print(os.environ["DEXCOM_ACCESS_TOKEN"])
    if access_token:

        global egv_data
        if not egv_data:
            update_egv_data()
        return render_template("index.html", egv=egv_data.get('egv'))
    else:
        return redirect(url_for('login'))

@app.route("/get_egv_data")  # Endpoint for client-side updates
def get_egv_data():
    global egv_data
    return jsonify({'egv': egv_data.get('egv') if egv_data else None})

@app.route('/login')
def login():
    auth_url = f"https://sandbox-api.dexcom.com/v2/oauth2/login?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=offline_access&state=hi"
    return redirect(auth_url)

@app.route("/authorize")
def handle_authorization():
    if 'code' in request.args:
        global access_token
        authorization_code = request.args.get('code')
        access_token = get_bearer_token(authorization_code)
        return redirect(url_for('home'))
    else:
        error = request.args.get('error')
        return f"Authorization denied: {error}"
