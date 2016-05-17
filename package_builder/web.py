from flask import Flask,render_template,request,session
from subprocess import Popen
import sys
import os
import time
import package_builder

app = Flask(__name__)    

# Sessions variables are stored client side, on the users browser
# the content of the variables is encrypted, so users can't
# actually see it. They could edit it, but again, as the content
# wouldn't be signed with this hash key, it wouldn't be valid
# You need to set a scret key (random text) and keep it secret
app.secret_key = 'F12Zr47j\3yX R~X@H!jmM]Lwf/,?KT'

@app.route("/")
def index():
    return render_template('index.html')

@app.route('/build', methods=['POST'])
def build():
    if session['sess_num'] == '':
        session['sess_num'] = str(time.time()).replace(".","")
    p = Popen(['/root/gotty', '-p', '8888', '--once', 'package_builder/package_builder.py', '-b', '-s', '/root/rpmbuild/SPECS/spec', '-o', '/root/rpmbuild/SOURCES/icecast-2.3.3.tar.gz', '-n', session['sess_num']])
    time.sleep(1)
    #if request.method == 'POST':
    #    if request.form['image'] == "centos": 
    return render_template('build.html', url="http://192.168.56.101:8888/", sess_num=session['sess_num'])

@app.route('/test', methods=['GET'])
def test():
    p = Popen(['/root/gotty', '-w', '-p', '8888', 'package_builder/package_builder.py', '-t', '-n', session['sess_num']])
    return render_template('test.html', url="http://192.168.56.101:8888/", sess_num=session['sess_num'])

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=8080)
