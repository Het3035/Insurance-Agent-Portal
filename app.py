from flask import Flask, render_template, request, redirect, session, flash
from db import *
import random
import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import os
load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

def generate_claim_id():
    return f"CLM{random.randint(100000,999999)}"


# ---------------- SMTP EMAIL FUNCTION ----------------
def send_email(to_email, subject, body):
    sender_email = os.getenv("EMAIL_USER")
    sender_password = os.getenv("EMAIL_PASS")

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'html'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, to_email, msg.as_string())
        server.quit()
        print(f"Email sent to {to_email}")
        return True
    except Exception as e:
        print("Error sending email:", e)
        return False


# ---------------- POLICY NUMBER ----------------
def generate_policy_no(company):
    rnd = random.randint(100, 999)
    if company == "TATA_AIG":
        return f"21040{rnd}"
    elif company == "NEW_INDIA":
        return f"19012{rnd}"
    return f"13045{rnd}"


# ---------------- HOME ----------------
@app.route("/")
def index():
    return render_template("index.html")


# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    invalid_login = False

    if request.method == "POST":
        agent = agents_collection.find_one({
            "email": request.form["email"],
            "password": request.form["password"]
        })

        if agent:
            session["agent_email"] = agent["email"]
            session["agent_name"] = agent["name"]
            return redirect("/dashboard")

        # ❌ Invalid credentials → show modal
        invalid_login = True

    return render_template("login.html", invalid_login=invalid_login)


# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if "agent_email" not in session:
        return redirect("/login")

    total = policies_collection.count_documents({})
    return render_template("dashboard.html", total_policies=total)


# ---------------- ADD POLICY ----------------
@app.route("/add-policy", methods=["GET", "POST"])
def add_policy():
    if request.method == "POST":
        session["member_count"] = int(request.form["member_count"])
        session["si"] = int(request.form["si"])
        return redirect("/member-ages")

    return render_template("add_policy.html")


# ---------------- MEMBER AGES ----------------
@app.route("/member-ages", methods=["GET", "POST"])
def member_ages():
    if "member_count" not in session:
        return redirect("/add-policy")

    if request.method == "POST":
        dobs = request.form.getlist("dob")

        ages = []
        dob_list = []

        today = datetime.date.today()

        for dob in dobs:
            dob_date = datetime.datetime.strptime(dob, "%Y-%m-%d").date()

            age = today.year - dob_date.year - (
                (today.month, today.day) < (dob_date.month, dob_date.day)
            )

            ages.append(age)
            dob_list.append(dob)

        session["ages"] = ages
        session["dobs"] = dob_list

        si = session["si"]

        members = []
        total = {"ICICI": 0, "NEW_INDIA": 0, "TATA_AIG": 0}

        for age in ages:
            ic = icici_quotes.find_one({
                "min_age": {"$lte": age},
                "max_age": {"$gte": age},
                "si": si
            })
            ni = new_india_quotes.find_one({
                "min_age": {"$lte": age},
                "max_age": {"$gte": age},
                "si": si
            })
            ta = tata_quotes.find_one({
                "min_age": {"$lte": age},
                "max_age": {"$gte": age},
                "si": si
            })

            ic_p = ic["premium"] if ic else 0
            ni_p = ni["premium"] if ni else 0
            ta_p = ta["premium"] if ta else 0

            members.append({
                "age": age,
                "ICICI": ic_p,
                "NEW_INDIA": ni_p,
                "TATA_AIG": ta_p
            })

            total["ICICI"] += ic_p
            total["NEW_INDIA"] += ni_p
            total["TATA_AIG"] += ta_p

        session["quote"] = {
            "si": si,
            "members": members,
            "total": total
        }

        return redirect("/select-company")

    return render_template("member_ages.html", count=session["member_count"])

# ---------------- SELECT COMPANY ----------------
@app.route("/select-company", methods=["GET","POST"])
def select_company():
    if "quote" not in session:
        return redirect("/add-policy")

    if request.method == "POST":
        session["company"] = request.form["company"]
        return redirect("/insured-details")

    return render_template(
        "select_company.html",
        q=session["quote"]
    )


# ---------------- INSURED DETAILS ----------------
@app.route("/insured-details", methods=["GET", "POST"])
def insured_details():

    # ---------------- SAFETY CHECK ----------------
    if "ages" not in session or "quote" not in session or "dobs" not in session:
        return redirect("/add-policy")

    ages = session["ages"]
    dobs = session["dobs"]

    if request.method == "POST":

        # ---------------- POLICY DATES ----------------
        start_date = datetime.datetime.strptime(
            request.form["start_date"], "%Y-%m-%d"
        )

        # ✅ UPDATED: FORCE END DATE = +1 YEAR (IGNORE FORM END DATE)
        end_date = start_date.replace(year=start_date.year + 1)

        # ---------------- PROPOSER ----------------
        proposer = {
            "name": request.form["proposer_name"],
            "aadhaar": request.form["proposer_aadhaar"],
            "age": ages[0],
            "dob": dobs[0],
            "contact": {
                "phone": request.form["proposer_mobile"],
                "email": request.form["proposer_email"]
            }
        }

        # ---------------- OTHER MEMBERS ----------------
        insured_members = []

        names = request.form.getlist("name[]")
        aadhaars = request.form.getlist("aadhaar[]")
        relations = request.form.getlist("relation[]")

        for i in range(len(names)):
            insured_members.append({
                "name": names[i],
                "aadhaar": aadhaars[i],
                "relation": relations[i],
                "age": ages[i + 1],
                "dob": dobs[i + 1]
            })

        # ---------------- POLICY OBJECT ----------------
        policy_no = generate_policy_no(session["company"])

        policy = {
            "policy_no": policy_no,
            "company": session["company"],
            "sum_insured": session["quote"]["si"],
            "remaining_sum_insured": session["quote"]["si"],
            "premium": session["quote"]["total"][session["company"]],
            "start_date": start_date,
            "end_date": end_date,
            "proposer": proposer,
            "insured_members": insured_members,
            "claims": []
        }

        policies_collection.insert_one(policy)

        # ---------------- SEND EMAIL ----------------
        proposer_email = proposer["contact"]["email"]

        subject = f"Policy Issued Successfully – {policy_no}"

        body = f"""
        <h3>Dear {proposer['name']},</h3>

        <p>Your insurance policy has been <strong>successfully issued</strong>.</p>

        <ul>
          <li><b>Policy Number:</b> {policy_no}</li>
          <li><b>Insurance Company:</b> {session['company']}</li>
          <li><b>Policy Period:</b>
              {start_date.strftime('%d-%m-%Y')}
              to
              {end_date.strftime('%d-%m-%Y')}
          </li>
          <li><b>Sum Insured:</b> ₹ {session['quote']['si']:,}</li>
          <li><b>Total Premium:</b> ₹ {session['quote']['total'][session['company']]:,}</li>
        </ul>

        <p>Warm regards,<br>
        <strong>Insurance Agent Portal</strong></p>
        """

        send_email(proposer_email, subject, body)

        # ---------------- CLEAR SESSION ----------------
        session.pop("ages", None)
        session.pop("dobs", None)
        session.pop("quote", None)
        session.pop("company", None)

        flash("Policy issued successfully and email sent to proposer", "success")
        return redirect("/view-policies")

    # ---------------- GET REQUEST ----------------
    return render_template(
        "insured_details.html",
        member_count=len(session["quote"]["members"]),
        ages=ages,
        dobs=dobs
    )



# ---------------- VIEW POLICIES ----------------
@app.route("/view-policies")
def view_policies():
    search = request.args.get("search", "")
    company = request.args.get("company", "")

    query = {}

    if search:
        query["$or"] = [
            {"policy_no": {"$regex": search, "$options": "i"}},
            {"proposer.contact.phone": {"$regex": search}},
            {"proposer.contact.email": {"$regex": search, "$options": "i"}}
        ]

    if company:
        query["company"] = company

    policies = policies_collection.find(query)
    now = datetime.datetime.now()

    return render_template(
        "view_policies.html",
        policies=policies,
        now=now,
        search=search,
        company=company
    )


# ---------------- POLICY DETAILS ----------------
@app.route("/policy/<policy_no>")
def policy_details(policy_no):
    policy = policies_collection.find_one({"policy_no": policy_no})
    if not policy:
        flash("Policy not found", "danger")
        return redirect("/view-policies")

    return render_template("policy_details.html", p=policy)


# ---------------- RENEW POLICY ----------------
@app.route("/renew-policy/<policy_no>", methods=["GET", "POST"])
def renew_policy(policy_no):

    policy = policies_collection.find_one({"policy_no": policy_no})

    if not policy:
        flash("Policy not found", "danger")
        return redirect("/view-policies")

    updated_members = policy.get("insured_members", [])
    premium = policy["premium"]

    if request.method == "POST":
        action = request.form.get("action")

        # ================= ADD MEMBER =================
        if action == "add":
            name = request.form["name"]
            aadhaar = request.form["aadhaar"]
            relation = request.form["relation"]
            dob = request.form["dob"]

            dob_date = datetime.datetime.strptime(dob, "%Y-%m-%d").date()
            today = datetime.date.today()

            age = today.year - dob_date.year - (
                (today.month, today.day) < (dob_date.month, dob_date.day)
            )

            company = policy["company"]

            if company == "ICICI":
                quote = icici_quotes.find_one({
                    "min_age": {"$lte": age},
                    "max_age": {"$gte": age},
                    "si": policy["sum_insured"]
                })
            elif company == "NEW_INDIA":
                quote = new_india_quotes.find_one({
                    "min_age": {"$lte": age},
                    "max_age": {"$gte": age},
                    "si": policy["sum_insured"]
                })
            elif company == "TATA_AIG":
                quote = tata_quotes.find_one({
                    "min_age": {"$lte": age},
                    "max_age": {"$gte": age},
                    "si": policy["sum_insured"]
                })
            else:
                quote = None

            extra = quote["premium"] if quote else 0

            updated_members.append({
                "name": name,
                "aadhaar": aadhaar,
                "relation": relation,
                "dob": dob,
                "age": age
            })

            premium += extra
            flash(f"Member added successfully (Age {age}, +₹{extra})", "success")

        # ================= REMOVE MEMBER =================
        elif action == "remove":
            index = int(request.form["member_index"])
            age = updated_members[index]["age"]
            company = policy["company"]

            if company == "ICICI":
                quote = icici_quotes.find_one({
                    "min_age": {"$lte": age},
                    "max_age": {"$gte": age},
                    "si": policy["sum_insured"]
                })
            elif company == "NEW_INDIA":
                quote = new_india_quotes.find_one({
                    "min_age": {"$lte": age},
                    "max_age": {"$gte": age},
                    "si": policy["sum_insured"]
                })
            elif company == "TATA_AIG":
                quote = tata_quotes.find_one({
                    "min_age": {"$lte": age},
                    "max_age": {"$gte": age},
                    "si": policy["sum_insured"]
                })
            else:
                quote = None

            minus = quote["premium"] if quote else 0
            updated_members.pop(index)
            premium -= minus

            flash(f"Member removed successfully (-₹{minus})", "warning")

        # ================= CHANGE COMPANY + SUM INSURED =================
        elif action == "change_company_si":
            new_company = request.form["company"]
            new_si = int(request.form["new_si"])

            total_premium = 0
            ages = [policy["proposer"]["age"]] + [m["age"] for m in policy["insured_members"]]

            for age in ages:
                if new_company == "ICICI":
                    quote = icici_quotes.find_one({"min_age": {"$lte": age}, "max_age": {"$gte": age}, "si": new_si})
                elif new_company == "NEW_INDIA":
                    quote = new_india_quotes.find_one({"min_age": {"$lte": age}, "max_age": {"$gte": age}, "si": new_si})
                elif new_company == "TATA_AIG":
                    quote = tata_quotes.find_one({"min_age": {"$lte": age}, "max_age": {"$gte": age}, "si": new_si})
                else:
                    quote = None

                total_premium += quote["premium"] if quote else 0

            policies_collection.update_one(
                {"policy_no": policy_no},
                {"$set": {
                    "company": new_company,
                    "sum_insured": new_si,
                    "remaining_sum_insured": new_si,
                    "premium": total_premium,
                    "claims": []
                }}
            )

            flash("Company & sum insured updated. Premium recalculated. Claims reset.", "success")
            return redirect(f"/renew-policy/{policy_no}")

        # ================= CHANGE SUM INSURED ONLY =================
        elif action == "change_si":
            new_si = int(request.form["new_si"])
            company = policy["company"]

            total_premium = 0
            ages = [policy["proposer"]["age"]] + [m["age"] for m in policy["insured_members"]]

            for age in ages:
                if company == "ICICI":
                    quote = icici_quotes.find_one({"min_age": {"$lte": age}, "max_age": {"$gte": age}, "si": new_si})
                elif company == "NEW_INDIA":
                    quote = new_india_quotes.find_one({"min_age": {"$lte": age}, "max_age": {"$gte": age}, "si": new_si})
                elif company == "TATA_AIG":
                    quote = tata_quotes.find_one({"min_age": {"$lte": age}, "max_age": {"$gte": age}, "si": new_si})
                else:
                    quote = None

                total_premium += quote["premium"] if quote else 0

            policies_collection.update_one(
                {"policy_no": policy_no},
                {"$set": {
                    "sum_insured": new_si,
                    "remaining_sum_insured": new_si,
                    "premium": total_premium,
                    "claims": []
                }}
            )

            flash("Sum insured updated & premium recalculated. Claims reset.", "success")
            return redirect(f"/renew-policy/{policy_no}")

        # ================= RENEW POLICY =================
        elif action == "renew":
            start_date = datetime.datetime.strptime(
                request.form["start_date"], "%Y-%m-%d"
            )

            # ✅ UPDATED: FORCE END DATE = +1 YEAR
            end_date = start_date.replace(year=start_date.year + 1)

            policies_collection.update_one(
                {"policy_no": policy_no},
                {"$set": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "remaining_sum_insured": policy["sum_insured"],
                    "claims": []
                }}
            )

            proposer_email = policy["proposer"]["contact"]["email"]

            subject = f"Policy Renewal Confirmation – {policy_no}"

            body = f"""
            <h3>Dear {policy['proposer']['name']},</h3>

            <p>Your insurance policy <strong>{policy_no}</strong>
            has been successfully renewed.</p>

            <ul>
              <li><b>Insurance Company:</b> {policy['company']}</li>
              <li><b>Policy Period:</b>
                  {start_date.strftime('%d-%m-%Y')}
                  to
                  {end_date.strftime('%d-%m-%Y')}
              </li>
              <li><b>Sum Insured:</b> ₹ {policy['sum_insured']:,}</li>
            </ul>

            <p>Warm regards,<br>
            <strong>Insurance Agent Portal</strong></p>
            """

            send_email(proposer_email, subject, body)

            flash("Policy renewed successfully and confirmation email sent.", "success")
            return redirect(f"/policy/{policy_no}")

        # ================= SAVE MEMBER & PREMIUM =================
        policies_collection.update_one(
            {"policy_no": policy_no},
            {"$set": {
                "insured_members": updated_members,
                "premium": premium
            }}
        )

        return redirect(f"/renew-policy/{policy_no}")

    return render_template("renew_policy.html", policy=policy)

# ---------------- DELETE POLICY ----------------
@app.route("/remove-policy/<policy_no>", methods=["POST"])
def remove_policy(policy_no):
    policies_collection.delete_one({"policy_no": policy_no})
    flash("Policy deleted successfully", "warning")
    return redirect("/view-policies")


# ---------------- REPORTS ----------------
@app.route("/reports")
def reports():
    if "agent_email" not in session:
        return redirect("/login")

    now = datetime.datetime.now()
    next_30_days = now + datetime.timedelta(days=30)

    # ================= POLICY STATS =================
    total_policies = policies_collection.count_documents({})

    company_report = list(policies_collection.aggregate([
        {"$group": {"_id": "$company", "count": {"$sum": 1}}}
    ]))

    premium_report = list(policies_collection.aggregate([
        {"$group": {"_id": "$company", "total_premium": {"$sum": "$premium"}}}
    ]))

    active_policies = policies_collection.count_documents({"end_date": {"$gte": now}})
    expired_policies = policies_collection.count_documents({"end_date": {"$lt": now}})

    upcoming = policies_collection.find({
        "end_date": {"$gte": now, "$lte": next_30_days}
    })

    # ================= CLAIM REPORT =================
    policies = policies_collection.find({})

    total_claims = 0
    total_claim_amount = 0
    claim_list = []

    for p in policies:
        for c in p.get("claims", []):
            total_claims += 1
            total_claim_amount += c.get("amount", 0)

            claim_list.append({
                "policy_no": p["policy_no"],
                "company": p["company"],
                "claimee": c.get("claimee_name"),
                "amount": c.get("amount"),
                "status": c.get("status"),
                "date": c.get("date")
            })

    return render_template(
        "reports.html",
        total_policies=total_policies,
        company_report=company_report,
        premium_report=premium_report,
        active_policies=active_policies,
        expired_policies=expired_policies,
        upcoming=upcoming,
        total_claims=total_claims,
        total_claim_amount=total_claim_amount,
        claim_list=claim_list
    )


# ---------------- SEND EMAILS FOR UPCOMING RENEWALS ----------------
@app.route("/send-renewal-email/<policy_no>", methods=["POST"])
def send_renewal_email(policy_no):
    if "agent_email" not in session:
        return redirect("/login")

    policy = policies_collection.find_one({"policy_no": policy_no})

    if not policy:
        flash("Policy not found", "danger")
        return redirect("/reports")

    proposer = policy["proposer"]
    email = proposer["contact"]["email"]

    expiry = policy["end_date"].strftime("%d-%m-%Y")

    subject = f"Policy Renewal Reminder – {policy_no}"

    body = f"""
    <h3>Dear {proposer['name']},</h3>

    <p>This is a gentle reminder that your insurance policy
    <strong>{policy_no}</strong> with <strong>{policy['company']}</strong>
    is going to expire on <strong>{expiry}</strong>.</p>

    <p>Please renew your policy before the expiry date to
    continue enjoying uninterrupted coverage.</p>

    <p><b>Sum Insured:</b> ₹ {policy['sum_insured']:,}</p>
    <p><b>Premium:</b> ₹ {policy['premium']:,}</p>

    <br>
    <p>For renewal assistance, please contact your insurance agent.</p>

    <p>Thank you,<br>
    <strong>Insurance Agent Portal</strong></p>
    """

    send_email(email, subject, body)

    flash(f"Renewal email sent to {email}", "success")
    return redirect("/reports")

# ---------------- CLAIMS ----------------
@app.route("/claims", methods=["GET", "POST"])
def claims():
    if "agent_email" not in session:
        return redirect("/login")

    policies = []
    no_policy = False

    if request.method == "POST":
        search = request.form["search"].strip()

        policies = list(policies_collection.find({
            "$or": [
                {"policy_no": search},
                {"proposer.contact.phone": search},
                {"proposer.contact.email": search}
            ]
        }))

        if not policies:
            no_policy = True

    return render_template(
        "claims.html",
        policies=policies,
        no_policy=no_policy
    )


# ---------------- CLAIM DETAILS & ADD CLAIM ----------------
@app.route("/claim/<policy_no>", methods=["GET", "POST"])
def claim_details(policy_no):
    policy = policies_collection.find_one({"policy_no": policy_no})

    if not policy:
        flash("Policy not found", "danger")
        return redirect("/claims")

    if request.method == "POST":
        amount = int(request.form["amount"])

        if amount > policy["remaining_sum_insured"]:
            flash("Claim amount exceeds remaining sum insured", "danger")
            return redirect(f"/claim/{policy_no}")

        claim = {
            "claim_id": generate_claim_id(),
            "claimee_name": request.form["claimee_name"],
            "claim_type": request.form["claim_type"],
            "amount": amount,
            "incident_date": datetime.datetime.strptime(
                request.form["incident_date"], "%Y-%m-%d"
            ),
            "description": request.form["description"],
            "status": "Approved",
            "created_at": datetime.datetime.now()
        }

        policies_collection.update_one(
            {"policy_no": policy_no},
            {
                "$push": {"claims": claim},
                "$inc": {"remaining_sum_insured": -amount}
            }
        )

        flash("Claim added successfully", "success")
        return redirect(f"/policy/{policy_no}")

    return render_template(
        "claim_details.html",
        policy=policy,
        proposer=policy["proposer"],
        members=policy["insured_members"]
    )

# ---------------- VIEW CLAIM DETAILS ----------------
@app.route("/claim-view/<policy_no>/<claim_id>")
def claim_view(policy_no, claim_id):
    policy = policies_collection.find_one({"policy_no": policy_no})

    if not policy:
        flash("Policy not found", "danger")
        return redirect("/view-policies")

    # 🔍 Find claim inside policy
    claim = None
    for c in policy.get("claims", []):
        if c["claim_id"] == claim_id:
            claim = c
            break

    if not claim:
        flash("Claim not found", "danger")
        return redirect(f"/policy/{policy_no}")

    return render_template(
        "claim_view.html",
        policy=policy,
        claim=claim
    )


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)


