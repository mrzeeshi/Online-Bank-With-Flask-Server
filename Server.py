from flask import Flask,render_template,request,redirect,session
import hashlib
import json
import random
import os
app=Flask(__name__,template_folder='.')
app.secret_key='my secret key'
error=''
with open ('data.json','r') as file:
    user=json.load(file)
@app.route('/signup',methods=['GET','POST'])
def home():
    error=''
    if request.method=='POST':
        firstname=request.form.get("fname")
        lastname=request.form.get("lname")
        phoneno=request.form.get("phone")
        email=request.form.get("mail")
        passs=request.form.get("pass")
        confpass=request.form.get("confpass")
        if confpass!=passs:
            error+=' The both passwords are different. '
        if not verify_pass(passs):
            error+=' The password is weak.It should be at least 8 characters long containing upper case lower case letters and digits and symbols'
        if not error:
            account_no=generate_random_card_info()
            username=generate_username(firstname)
            while account_no in user:
                account_no=generate_random_card_info()
            while username in user:
                username=generate_username(firstname)
            user_data={
                'name':firstname + lastname,
                'phone_no':phoneno,
                'email':email,
                'password':hashlib.sha256(passs.encode()).hexdigest(),
                'account_no':account_no,
                'username':username
            }
            user.append(user_data)        
            with open ('data.json','w') as file_to_write:
                json.dump(user,file_to_write,indent=4)
            return render_template('Login.html')
        else:
            return render_template('Signup.html' , error=error,
                                    fname=firstname,
                                    lname=lastname,
                                    phone=phoneno,
                                    email=email)
    else:
        return render_template('Signup.html')
@app.route('/login',methods=['POST','GET'])
def login():
    if (request.method=='POST'):
        email=request.form.get('mail')
        password=request.form.get('pass')
        pass_hash=hashlib.sha256(password.encode()).hexdigest()
        with open ('data.json','r') as file:
            users_data=json.load(file)
        for user in users_data:
            if (pass_hash==user["password"] and email==user["email"]):
                session['email']=email
                name=user['name']
                username=user['username']
                card_no=user['account_no']
                message={
                    'name':name,
                    'username':username,
                    'card_no':card_no
                }
                return render_template('Dashboard.html',message=message)
        return render_template('Login.html',error=email)
    else:
        return render_template('Login.html')
@app.route('/send-money' , methods=['GET','POST'])
def sendmoney():
    if request.method=='POST':
        email=session['email']
        receiver=request.form['recipient']
        amount=request.form['amount']
@app.route('/Dashboard')
def dashboard():
    return render_template('Dashboard.html')
symbs = "!@#$%^&*()_+-=[]{}|;:',.<>?/"
def verify_pass(password):
    return (
        len(password) >= 8
        and any(c.isupper() for c in password)
        and any(c.islower() for c in password)
        and any(c.isdigit() for c in password)
        and any(c in symbs for c in password)
    )
def generate_random_card_info():
    first=str(random.randint(1000,9999))
    second=str(random.randint(1000,9999))
    third=str(random.randint(1000,9999))
    fourth=str(random.randint(1000,9999))
    return str(first+' '+second+' '+third+' '+fourth)
def generate_username(firstname):
    username=firstname
    random_chars='1234567890abcdefghijklmnopqrstuvwxyz'
    username+=''.join(random.sample(random_chars,k=5))
    return username
if __name__=='__main__':
    app.run(debug=True)
