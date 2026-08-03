from flask import Flask,render_template,request,redirect
app=Flask(__name__,template_folder='.')
@app.route('/signup')
def home():
    return render_template('Signup.html' , error='this is the error')
if __name__=='__main__':
    app.run(debug=True)