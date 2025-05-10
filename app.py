from flask import Flask, request, jsonify
import pymysql
import re
import requests
from datetime import datetime

app = Flask(__name__)

# DB Config
conn = pymysql.connect(
    host="localhost",
    user="your_db_user",
    password="your_db_pass",
    database="your_db_name"
)

# Dummy token checker (replace with your actual implementation)
def check_token(token):
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM token_table WHERE token = %s", (token,))
    result = cursor.fetchone()
    cursor.close()
    return result[0] if result else False

@app.route('/upi/check', methods=['GET'])
def check_upi():
    txn_id = request.args.get('txn_id', '').strip()
    token = request.args.get('token', '').strip()

    if not txn_id:
        return jsonify(status="500", message="Invalid txn id")

    if not token:
        return jsonify(status="500", message="Token Blank")

    user_id = check_token(token)
    if not user_id:
        return jsonify(status="500", message="Token Expired Please Logout And Login Again")

    if not re.match(r'^[a-zA-Z0-9 ]+$', txn_id):
        return jsonify(status="500", message="Symbol Not Allowed")
    if len(txn_id) > 12:
        return jsonify(status="500", message="Utr Not More Than 12 Digits")
    if txn_id[0] == '0':
        return jsonify(status="500", message="Invalid Utr Enter")

    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM upi_recharge WHERE txn_id=%s", (txn_id,))
    if cursor.fetchone():
        return jsonify(status="500", message="Utr id Already Used")

    cursor.execute("SELECT * FROM user_wallet WHERE user_id=%s", (user_id,))
    user_data = cursor.fetchone()
    user_balance = float(user_data['balance'])
    total_recharge = float(user_data['total_recharge'])

    # Fetch site_data
    cursor.execute("SELECT upi_merchant_id, upi_merchant_token, upi_min_recharge FROM site_settings LIMIT 1")
    site_data = cursor.fetchone()
    upi_merchant = site_data['upi_merchant_id']
    upi_token = site_data['upi_merchant_token']
    min_recharge = float(site_data['upi_min_recharge'])

    url = f"https://payments-tesseract.bharatpe.in/api/v1/merchant/transactions?module=PAYMENT_QR&merchantId={upi_merchant}"
    headers = {"token": upi_token}
    r = requests.get(url, headers=headers)
    transactions = r.json().get('data', {}).get('transactions', [])

    for transaction in transactions:
        if transaction['bankReferenceNo'] == txn_id:
            amount = float(transaction['amount'])
            if amount >= min_recharge:
                payee_name = transaction['payerName']
                payee_handle = transaction['payerHandle']
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                new_balance = user_balance + amount
                new_total_recharge = total_recharge + amount

                cursor.execute("INSERT INTO upi_recharge (user_id, amount, txn_id, recharge_time, status) VALUES (%s, %s, %s, %s, 1)", 
                               (user_id, amount, txn_id, current_time))
                cursor.execute("UPDATE user_wallet SET balance=%s, total_recharge=%s WHERE user_id=%s", 
                               (new_balance, new_total_recharge, user_id))
                cursor.execute("INSERT INTO user_transaction (user_id, amount, date, type, txn_id, status) VALUES (%s, %s, %s, 'Upi Recharge', %s, 1)",
                               (user_id, amount, current_time, txn_id))
                conn.commit()
                cursor.close()
                return jsonify(status="200", message=f"{amount}Rs Credit In Your Account")
            else:
                cursor.close()
                return jsonify(status="500", message=f"You Have Pay Less Than {min_recharge} Rs Contact Our Support Team")

    cursor.close()
    return jsonify(status="500", message="Payment Not Found")

if __name__ == '__main__':
    app.run(debug=True)
