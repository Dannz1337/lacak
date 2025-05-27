from flask import Flask, render_template, request
import os
from lokasi import proses_file

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/", methods=["GET", "POST"])
def index():
    hasil = None
    if request.method == "POST":
        file = request.files["media"]
        if file:
            path = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(path)
            hasil = proses_file(path)
    return render_template("index.html", hasil=hasil)

if __name__ == "__main__":
    app.run(debug=True)