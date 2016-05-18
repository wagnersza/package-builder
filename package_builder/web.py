from flask import Flask,render_template,request,session
from subprocess import Popen
import sys
import os
import time
import package_builder
from werkzeug import secure_filename

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
    web_upload_files = "web_upload_files_%s" % session['sess_num']
    if not os.path.exists(web_upload_files):
        os.makedirs(web_upload_files)
    image = request.form['image']
    file_spec = request.files['spec']
    file_source = request.files['source']
    if file_spec.filename == '' or file_source.filename == '' or image == '':
        return render_template('index.html', error="Error: The image, Spec or Source file was(were) not not specified")
    session['image'] = image
    file_spec.save(os.path.join(web_upload_files, file_spec.filename))
    file_source.save(os.path.join(web_upload_files, file_source.filename))
    p = Popen(['/root/gotty -p 8888 --once package_builder/package_builder.py -b -s ./'+ web_upload_files +'/'+ file_spec.filename +' -o ./'+ web_upload_files +'/'+ file_source.filename +' -i '+ image +' -n '+ session['sess_num']], shell=True)
    time.sleep(1)
    return render_template('build.html', url="http://192.168.56.101:8888/", sess_num=session['sess_num'])

@app.route('/test', methods=['GET'])
def test():
    p = Popen(['/root/gotty -w -p 8888 --once package_builder/package_builder.py -t -i '+ session['image'] +' -n '+ session['sess_num'] +' && docker stop package-builder'], shell=True)
    time.sleep(1)
    return render_template('test.html', url="http://192.168.56.101:8888/", sess_num=session['sess_num'])

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=8080)
