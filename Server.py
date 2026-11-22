from flask import (Flask, render_template, request, redirect, session,
                   url_for, flash, get_flashed_messages)
from functools import wraps
from datetime import datetime, date
import hashlib
import hmac
import json
import math
import os
import random
import pandas as pd

app = Flask(__name__, template_folder='.')
app.secret_key = os.environ.get('ZEEBANK_SECRET', 'change-me-before-deploying')

USERS_FILE = 'data.json'
TRANSACTIONS_FILE = 'transactions.csv'
REQUESTS_FILE = 'money_requests.csv'
TRANSACTION_COLUMNS = ['sender', 'receiver', 'amount', 'type', 'date', 'time', 'day']
MAX_AMOUNT = 10_000_000
RECENT_COUNT = 5
BILLERS = {'electricity', 'gas', 'water', 'internet', 'mobile', 'other'}
FUNDING_SOURCES = {'bank_account', 'debit_card', 'cash_deposit'}
BAD_AMOUNT = 'Enter a valid amount between 0.01 and 10,000,000.'
symbs = "!@#$%^&*()_+-=[]{}|;:',.<>?/"

if os.path.exists(USERS_FILE) and os.path.getsize(USERS_FILE) > 0:
    with open(USERS_FILE, 'r') as file:
        users = json.load(file)
else:
    users = []


# ================= HELPERS =================

def save_users():
    with open(USERS_FILE, 'w') as file:
        json.dump(users, file, indent=4)


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def verify_pass(password):
    return (
        len(password) >= 8
        and any(c.isupper() for c in password)
        and any(c.islower() for c in password)
        and any(c.isdigit() for c in password)
        and any(c in symbs for c in password)
    )


def generate_random_card_info():
    return ' '.join(str(random.randint(1000, 9999)) for _ in range(4))


def generate_username(firstname):
    random_chars = '1234567890abcdefghijklmnopqrstuvwxyz'
    return firstname + ''.join(random.sample(random_chars, k=5))


def find_user_by_email(email):
    if not email:
        return None
    email = email.strip().lower()
    return next((u for u in users if u['email'].lower() == email), None)


def find_recipient(identifier):
    """Match by username, account number (spaces ignored) or email."""
    identifier = (identifier or '').strip()
    if not identifier:
        return None
    compact = identifier.replace(' ', '')
    for u in users:
        if (u['username'] == identifier
                or u['account_no'].replace(' ', '') == compact
                or u['email'].lower() == identifier.lower()):
            return u
    return None


def parse_amount(raw):
    try:
        amount = round(float(raw), 2)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(amount) or amount <= 0 or amount > MAX_AMOUNT:
        return None
    return amount


def log_transaction(sender, receiver, amount, tx_type):
    now = datetime.now()
    row = pd.DataFrame([{
        'sender': sender,
        'receiver': receiver,
        'amount': amount,
        'type': tx_type,
        'date': now.strftime('%Y:%m:%d'),
        'time': now.strftime('%H:%M:%S'),
        'day': now.strftime('%A')
    }])
    row.to_csv(TRANSACTIONS_FILE, mode='a', header=False, index=False)


def name_of(email):
    u = find_user_by_email(email)
    return u['name'] if u else email


def get_recent_transactions(email, limit=RECENT_COUNT):
    if not os.path.exists(TRANSACTIONS_FILE) or os.path.getsize(TRANSACTIONS_FILE) == 0:
        return []
    df = pd.read_csv(TRANSACTIONS_FILE, names=TRANSACTION_COLUMNS)
    mine = df[(df['sender'] == email) | (df['receiver'] == email)].tail(limit).iloc[::-1]
    result = []
    for _, r in mine.iterrows():
        incoming = r['receiver'] == email
        if r['type'] == 'bill':
            label = 'Bill: ' + str(r['receiver']).split(':')[0].title()
        elif r['type'] == 'deposit':
            label = 'Deposit: ' + str(r['sender']).replace('_', ' ').title()
        else:
            label = name_of(r['sender'] if incoming else r['receiver'])
        result.append({
            'label': label,
            'amount': float(r['amount']),
            'incoming': incoming,
            'category': r['type'],
            'when': str(r['date']).replace(':', '-') + ' ' + str(r['time'])[:5],
        })
    return result


def current_user():
    return find_user_by_email(session.get('email'))


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user() is None:
            session.clear()
            return redirect(url_for('login'))
        return view(*args, **kwargs)
    return wrapped


def render_dashboard(user, **extra):
    message = {
        'name': user['name'],
        'username': user['username'],
        'card_no': user['account_no'],
        'balance': user['balance'],
        'notice': ' '.join(get_flashed_messages()),
    }
    message.update(extra)
    return render_template(
        'Dashboard.html',
        message=message,
        date=date.today().strftime('%B %d, %Y'),
        transactions=get_recent_transactions(user['email']),
    )


# ================= AUTH =================

@app.route('/')
def index():
    return redirect(url_for('login'))


@app.route('/signup', methods=['GET', 'POST'])
def home():
    if request.method != 'POST':
        return render_template('Signup.html')

    firstname = request.form.get("fname", "").strip()
    lastname = request.form.get("lname", "").strip()
    phoneno = request.form.get("phone", "").strip()
    email = request.form.get("mail", "").strip()
    passs = request.form.get("pass", "")
    confpass = request.form.get("confpass", "")

    error = ''
    if confpass != passs:
        error += ' The both passwords are different. '
    if not verify_pass(passs):
        error += (' The password is weak. It should be at least 8 characters long '
                  'containing upper case lower case letters and digits and symbols')
    if find_user_by_email(email):
        error += ' An account with this email already exists. '

    if error:
        return render_template('Signup.html', error=error, fname=firstname,
                               lname=lastname, phone=phoneno, email=email)

    existing_accounts = {u['account_no'] for u in users}
    existing_usernames = {u['username'] for u in users}
    account_no = generate_random_card_info()
    while account_no in existing_accounts:
        account_no = generate_random_card_info()
    username = generate_username(firstname)
    while username in existing_usernames:
        username = generate_username(firstname)

    users.append({
        'name': f'{firstname} {lastname}',
        'phone_no': phoneno,
        'email': email,
        'password': hash_password(passs),
        'account_no': account_no,
        'username': username,
        'balance': 0
    })
    save_users()
    return redirect(url_for('login'))


@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        email = request.form.get('mail', '').strip()
        pass_hash = hash_password(request.form.get('pass', ''))
        user = find_user_by_email(email)
        if user and hmac.compare_digest(pass_hash, user['password']):
            session.clear()
            session['email'] = user['email']
            return redirect(url_for('dashboard'))
        return render_template('Login.html', error=email)
    return render_template('Login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/Dashboard')
@login_required
def dashboard():
    return render_dashboard(current_user())


# ================= MONEY ROUTES =================

@app.route('/send-money', methods=['POST'])
@login_required
def sendmoney():
    sender = current_user()
    receiver = find_recipient(request.form.get('recipient'))
    amount = parse_amount(request.form.get('amount'))

    error = None
    if amount is None:
        error = BAD_AMOUNT
    elif receiver is None:
        error = "No user found with that username or account number."
    elif receiver is sender:
        error = "You can't send money to yourself."
    elif amount > sender['balance']:
        error = 'Insufficient balance.'

    if error:
        return render_dashboard(sender, messagee=error, open_modal='send')

    sender['balance'] = round(sender['balance'] - amount, 2)
    receiver['balance'] = round(receiver['balance'] + amount, 2)
    save_users()
    log_transaction(sender['email'], receiver['email'], amount, 'sent')
    flash(f"Sent ${amount:,.2f} to {receiver['name']}.")
    return redirect(url_for('dashboard'))


@app.route('/receive-money', methods=['POST'])
@login_required
def receive_money():
    """Creates a money REQUEST to another user (no balance change yet)."""
    me = current_user()
    payer = find_recipient(request.form.get('recipient'))
    amount = parse_amount(request.form.get('amount'))

    error = None
    if amount is None:
        error = BAD_AMOUNT
    elif payer is None:
        error = "No user found with that username or account number."
    elif payer is me:
        error = "You can't request money from yourself."

    if error:
        return render_dashboard(me, messagee=error, open_modal='receive')

    now = datetime.now()
    row = pd.DataFrame([{
        'requester': me['email'],
        'payer': payer['email'],
        'amount': amount,
        'status': 'pending',
        'date': now.strftime('%Y:%m:%d'),
        'time': now.strftime('%H:%M:%S'),
    }])
    row.to_csv(REQUESTS_FILE, mode='a', header=not os.path.exists(REQUESTS_FILE), index=False)
    flash(f"Requested ${amount:,.2f} from {payer['name']}.")
    return redirect(url_for('dashboard'))


@app.route('/pay-bill', methods=['POST'])
@login_required
def pay_bill():
    user = current_user()
    biller = request.form.get('biller', '')
    bill_account = request.form.get('bill_account', '').strip()
    amount = parse_amount(request.form.get('amount'))

    error = None
    if biller not in BILLERS:
        error = 'Please select a valid biller.'
    elif not (4 <= len(bill_account) <= 20 and bill_account.replace('-', '').isalnum()):
        error = 'Enter a valid consumer / account number (4-20 letters or digits).'
    elif amount is None:
        error = BAD_AMOUNT
    elif amount > user['balance']:
        error = 'Insufficient balance.'

    if error:
        return render_dashboard(user, messagee=error, open_modal='bills')

    user['balance'] = round(user['balance'] - amount, 2)
    save_users()
    log_transaction(user['email'], f'{biller}:{bill_account}', amount, 'bill')
    flash(f'Paid ${amount:,.2f} to {biller.title()} bill.')
    return redirect(url_for('dashboard'))


@app.route('/add-funds', methods=['POST'])
@login_required
def add_funds():
    user = current_user()
    source = request.form.get('funding_source', '')
    amount = parse_amount(request.form.get('amount'))

    error = None
    if source not in FUNDING_SOURCES:
        error = 'Please select a valid funding source.'
    elif amount is None:
        error = BAD_AMOUNT

    if error:
        return render_dashboard(user, messagee=error, open_modal='funds')

    user['balance'] = round(user['balance'] + amount, 2)
    save_users()
    log_transaction(source, user['email'], amount, 'deposit')
    flash(f'Added ${amount:,.2f} to your account.')
    return redirect(url_for('dashboard'))


if __name__ == '__main__':
    app.run(debug=True)
