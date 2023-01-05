# bug/fix: duplicate pdf reports generated from similar names, insted of "in" should be "==" might need full path?

import os
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, send_from_directory
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
from helpers import makePDF, makeFinalPDF, convert_data
from datetime import datetime
from flask_mail import Mail, Message

# Configure application
app = Flask(__name__)

# Necessary configs
app.config['UPLOAD_DIRECTORY'] = 'static/files'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # 16MB
app.config['ALLOWED_EXTENSIONS'] = ['.jpg', '.jpeg', '.png', '.gif']
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Configure mail settings
app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'mdxqc5000@gmail.com'
app.config['MAIL_PASSWORD'] = 'fvyorhwcsleyxzvf'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
mail = Mail(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///qc.db")

# Declare constant variables
benches = ["PCR1", "PCR2", "PCR3", "LC1", "LC2", "Midshift"]
yea_nea = ["Pass", "Fail"]
yea_nea2 = ["Approve", "Reject"]
status = ["Pending", "In Review", "Final", "Fail"]

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Home page route
@app.route("/")
def index():
    x_db = db.execute("SELECT COUNT(reagent) FROM qc WHERE status=?", status[0])
    x = x_db[0]["COUNT(reagent)"]
    y_db = db.execute("SELECT COUNT(reagent) FROM qc WHERE status=?", status[1])
    y = y_db[0]["COUNT(reagent)"]
    bench_count_list = []
    z_db = db.execute("SELECT bench, COUNT(reagent), prepared FROM qc WHERE status=? GROUP BY bench", status[0])
    for dic in z_db:
        temp_list = (list(dic.values()))
        bench_count_list.append(temp_list)

    today = datetime.now()

    print(bench_count_list)

    # feature: add amount of time each qc has been pending for

    return render_template("index.html", x=x, y=y, bench_count_list=bench_count_list)

# CLT route
@app.route("/clt", methods= ["GET", "POST"])
def clt():
    # Collect and store user responses when CLT form is submitted
    if request.method == "POST":
        received = request.form.get("received")
        prepared = request.form.get("prepared")
        expired = request.form.get("expired")
        newlot = request.form.get("newlot")
        currentlot = request.form.get("currentlot")
        reagent = request.form.get("reagent")
        bench = request.form.get("bench")

        # Ensure valid user input when submitting CLT form
        if not received or not prepared or not expired or not newlot or not currentlot or not reagent or not bench or bench not in benches:
            return "Ensure all information is valid"
            # bug/fixes: need to flash message on same page with error instead of redirecting to new page.
        else:
            # Insert responses from CLT form into database
            db.execute("INSERT INTO qc (reagent, newlot, currentlot, received, prepared, expired, bench) VALUES(?, ?, ?, ?, ?, ?, ?)", reagent, newlot, currentlot, received, prepared, expired, bench)
        return redirect("/")
    else:
        return render_template("clt.html", benches=benches)

# MLS route
@app.route("/mls", methods=["GET", "POST"])
def mls():
    # Select relavent information from database to display on MLS page
    qc_db = db.execute("SELECT id, attempt, bench, reagent, currentlot, newlot, comment FROM qc WHERE status=?", status[0])
    return render_template("mls.html", qc_db=qc_db, yea_nea=yea_nea)

# Upload route
@app.route("/upload", methods=["POST"])
def upload():
    try:
        # retrieve image file, ensure image validity and save to upload directory
        file = request.files["file"]
        extension = os.path.splitext(file.filename)[1].lower()

        if file:
            if extension not in app.config["ALLOWED_EXTENSIONS"]:
                return "File is not a valid extension (jpg, jpeg, png)"
            file.save(os.path.join(app.config['UPLOAD_DIRECTORY'], secure_filename(file.filename)))
        else:
            return "File not attached"

        # Collect and store user responses when MLS form is submitted
        id = request.form.get("id")
        initials = request.form.get("initials")
        qc_date = request.form.get("QC'd")
        pass_fail = request.form.get("pass_fail")
        comment = request.form.get("comment")

        # Ensure valid user input when submitting MLS form
        if not id or not initials or not qc_date or not pass_fail or pass_fail not in yea_nea:
            return "Ensure all information entered is valid"
            # bug/fixes: error checking for ids only present in pending status?
        # Honestly this is pointless but I'm too lazy to fix it now
        if pass_fail == "Pass":
            pass_fail = True
        else:
            pass_fail = False

        # Read image file in binary to be stored in database. Honestly, is this necessary?
        with open(os.path.join(app.config['UPLOAD_DIRECTORY'], secure_filename(file.filename)), "rb") as f:
            blobs = f.read()

        # Logic for updating attempt number if QC fails
        curr_attempt_db = db.execute("SELECT attempt FROM qc WHERE id=?", id)
        curr_attempt = curr_attempt_db[0]["attempt"]
        new_attempt = curr_attempt + 1

        if pass_fail == False and curr_attempt == 1:
            db.execute("UPDATE qc SET attempt=?, pic1=?, initials=?, QC_date=?, pass=?, status=?, pic1_name=?, comment=? WHERE id=?", new_attempt, blobs, initials, qc_date, pass_fail, status[0], secure_filename(file.filename), comment, id)

        elif pass_fail == False and curr_attempt == 2:
            db.execute("UPDATE qc SET attempt=?, pic2=?, initials=?, QC_date=?, pass=?, status=?, pic2_name=?, comment=? WHERE id=?", new_attempt, blobs, initials, qc_date, pass_fail, status[0], secure_filename(file.filename), comment, id)

        elif pass_fail == False and curr_attempt == 3:
            db.execute("UPDATE qc SET pic3=?, initials=?, QC_date=?, pass=?, status=?, pic3_name=?, comment=? WHERE id=?", blobs, initials, qc_date, pass_fail, status[3], secure_filename(file.filename), comment, id)

        # Generate a preliminary pdf for review if QC passes and save path to database
        else:
            db.execute("UPDATE qc SET pic3=?, initials=?, QC_date=?, pass=?, status=?, pic3_name=?, comment=? WHERE id=?", blobs, initials, qc_date, pass_fail, status[1], secure_filename(file.filename), comment, id)
            pdf_db = db.execute("SELECT reagent, newlot, currentlot, received, prepared, expired, initials, QC_date, comment, pic3_name, pic1_name, pic2_name FROM qc WHERE id=?", id)
            pdf_reagent = pdf_db[0]["reagent"]
            pdf_newlot = pdf_db[0]["newlot"]
            pdf_currentlot = pdf_db[0]["currentlot"]
            pdf_received = pdf_db[0]["received"]
            pdf_prepared = pdf_db[0]["prepared"]
            pdf_expired = pdf_db[0]["expired"]
            pdf_initials = pdf_db[0]["initials"]
            pdf_QC_date = pdf_db[0]["QC_date"]
            pdf_comment = pdf_db[0]["comment"]
            pic3 = pdf_db[0]["pic3_name"]
            pic1 = pdf_db[0]["pic1_name"]
            pic2 = pdf_db[0]["pic2_name"]
            pdf_list = [pdf_reagent, pdf_newlot, pdf_currentlot, pdf_received, pdf_prepared, pdf_expired, pdf_initials, pdf_QC_date, pdf_comment]
            makePDF(pdf_list, f"static/files/{pic3}", f"static/files/{pic1}", f"static/files/{pic2}")
            # bugs/fixes: MAJOR ISSUE = need to account for special characters in input fields "/, ;, etc."
            pdf_path = os.path.abspath(f"static/pdfs/{pdf_reagent}.pdf")
            db.execute("UPDATE qc SET pdf_path=? WHERE id=?", pdf_path, id)

            # Send email notification to reviewer
            msg = Message("New QC Report For Review", sender=app.config['MAIL_USERNAME'], recipients=["nagutm@uw.edu"])
            msg.body = f"Hello, there is a new QC report for {pdf_reagent} available for you to review."
            mail.send(msg)

    except RequestEntityTooLarge:
        return "File is larger than 16MB"
    return redirect("/mls")

# Review route
@app.route("/review", methods=["GET", "POST"])
def review():
    # Store preliminary pdfs in a list for future retrieval
    pdfs = os.listdir("static/pdfs")
    pdf_list = []
    for pdf in pdfs:
        pdf_list.append(pdf)
    if request.method == "POST":
        # Collect and store user responses when Review form is submitted
        id = request.form.get("id")
        reviewed = request.form.get("reviewed")
        review_initials = request.form.get("review_initials")
        pass_fail2 = request.form.get("pass_fail2")

        # Ensure valid user input when submitting Review form
        if not id or not review_initials or not reviewed or not pass_fail2 or pass_fail2 not in yea_nea2:
            return "Ensure all information entered is valid"
            # bug/fixes: error checking for ids in review queue?

        # Generate final pdf if QC is approved and update database
        if pass_fail2 == "Approve":
            db.execute("UPDATE qc SET review_date=?, review_initials=? WHERE id=?", reviewed, review_initials, id)
            pdf_db2 = db.execute("SELECT reagent, newlot, currentlot, received, prepared, expired, initials, QC_date, comment, review_date, review_initials, pic3_name, pic1_name, pic2_name FROM qc WHERE id=?", id)
            pdf_reagent = pdf_db2[0]["reagent"]
            pdf_newlot = pdf_db2[0]["newlot"]
            pdf_currentlot = pdf_db2[0]["currentlot"]
            pdf_received = pdf_db2[0]["received"]
            pdf_prepared = pdf_db2[0]["prepared"]
            pdf_expired = pdf_db2[0]["expired"]
            pdf_initials = pdf_db2[0]["initials"]
            pdf_QC_date = pdf_db2[0]["QC_date"]
            pdf_comment = pdf_db2[0]["comment"]
            pdf_review_date = pdf_db2[0]["review_date"]
            pdf_review_initials = pdf_db2[0]["review_initials"]
            pic3 = pdf_db2[0]["pic3_name"]
            pic1 = pdf_db2[0]["pic1_name"]
            pic2 = pdf_db2[0]["pic2_name"]
            pdf_list2 = [pdf_reagent, pdf_newlot, pdf_currentlot, pdf_received, pdf_prepared, pdf_expired, pdf_initials, pdf_QC_date, pdf_comment, pdf_review_date, pdf_review_initials]
            makeFinalPDF(pdf_list2, f"static/files/{pic3}", f"static/files/{pic1}", f"static/files/{pic2}")
            # bug/fixes: need to account for special characters in input fields "/, ;, etc."
            pdf_path2 = os.path.abspath(f"static/final_pdfs/{pdf_reagent}.pdf")
            db.execute("UPDATE qc SET final_path=?, status=? WHERE id=?", pdf_path2, status[2], id)
        else:
            db.execute("UPDATE qc SET status=? WHERE id=?", status[3], id)
        return redirect("/review")

    # Select relavent information from database to display on Review page
    else:
        review_db = db.execute("SELECT id, attempt, reagent, pdf_path FROM qc WHERE status=?", status[1])
        return render_template("review.html", review_db=review_db, yea_nea2=yea_nea2, pdf_list=pdf_list)

# Serve PDF route
@app.route("/serve-pdf/<filename>", methods=["GET", "POST"])
def serve_pdf(filename):
    return send_from_directory("static/pdfs", filename)
    # bugs/fixes =  problem files with identical reagent names. need to make pdf name more specific(with date of qc?)

# Records route
@app.route("/records")
def records():
    final_pdfs = os.listdir("static/final_pdfs")
    final_pdf_list = []
    for pdf in final_pdfs:
        final_pdf_list.append(pdf)
    if request.method == "POST":
        ...
        # Search bar implementation
    else:
        records_db = db.execute("SELECT id, status, newlot, reagent, review_date, final_path FROM qc WHERE status=? OR status=?", status[2], status[3])
        return render_template("records.html", records_db=records_db, final_pdf_list=final_pdf_list)

# Serve final PDF route
@app.route("/serve-finalpdf/<filename>", methods=["GET", "POST"])
def serve_final_pdf(filename):
    return send_from_directory("static/final_pdfs", filename)
    # bugs/fixes =  problem files with identical reagent names. need to make pdf name more specific(with date of qc?)


if __name__ == "__main__":
  app.run(debug=True)