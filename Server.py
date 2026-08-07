from flask import Flask,render_template,request,redirect
import hashlib
import json
app=Flask(__name__,template_folder='.')
error=''
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
            user_data={
                'name':firstname + lastname,
                'phone_no':phoneno,
                'email':email,
                'password':hashlib.sha256(passs.encode()).hexdigest()
                
            }
            with open ('data.json','r') as file:
                user=json.load(file)
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
                return render_template('Dashboard.html')
        return render_template('Login.html',error=email)
    else:
        return render_template('Login.html')
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
if __name__=='__main__':
    app.run(debug=True)
