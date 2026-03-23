"""
Bakong KHQR Payment API
Flask REST API for generating and checking Bakong KHQR payment QR codes.
"""

import os
import uuid
from flask import Flask, request, jsonify
from flask_cors import CORS
from bakong_khqr import KHQR

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests

# ─── Config ───────────────────────────────────────────────────────────────────
BAKONG_TOKEN = os.environ.get("BAKONG_TOKEN", "YOUR_BAKONG_DEVELOPER_TOKEN_HERE")
BANK_ACCOUNT  = os.environ.get("BANK_ACCOUNT",  "davy_dorn@aclb")       # e.g. john@aclb
MERCHANT_NAME = os.environ.get("MERCHANT_NAME", "CT Service")
MERCHANT_CITY = os.environ.get("MERCHANT_CITY", "Phnom Penh")
PHONE_NUMBER  = os.environ.get("PHONE_NUMBER",  "85512345678")
STORE_LABEL   = os.environ.get("STORE_LABEL",   "CT Service")

khqr = KHQR(BAKONG_TOKEN)

# ─── Helpers ──────────────────────────────────────────────────────────────────
def make_bill_number():
    """Generate a unique bill/transaction reference number."""
    return "TRX" + uuid.uuid4().hex[:10].upper()


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "service": "Bakong KHQR Payment API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "POST /api/qr/generate": "Generate a new KHQR payment QR code",
            "GET  /api/qr/check/<md5>": "Check payment status by MD5 hash",
            "POST /api/qr/check-bulk": "Check multiple payments at once",
            "GET  /api/payment/<md5>": "Get full payment transaction info",
            "GET  /api/health": "Health check"
        }
    })


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/api/qr/generate", methods=["POST"])
def generate_qr():
    """
    Generate a Bakong KHQR payment QR code.

    Body (JSON):
        amount       float   required  Payment amount
        currency     str     optional  "KHR" or "USD" (default: USD)
        bill_number  str     optional  Custom bill reference (auto-generated if omitted)
        terminal     str     optional  Terminal/cashier label
        static       bool    optional  True for static QR (default: False = dynamic)
        callback     str     optional  Deeplink callback URL
        app_icon     str     optional  Icon URL for deeplink

    Returns:
        qr_string    str   Raw KHQR string
        md5          str   MD5 hash for payment checking
        bill_number  str   Transaction reference
        deeplink     str   Bakong deeplink (if callback provided)
        qr_image_b64 str   Base64 QR code image (PNG)
    """
    data = request.get_json(force=True) or {}

    # Validate required fields
    amount = data.get("amount")
    if amount is None:
        return jsonify({"error": "amount is required"}), 400
    try:
        amount = float(amount)
        if amount <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"error": "amount must be a positive number"}), 400

    currency    = str(data.get("currency", "USD")).upper()
    if currency not in ("USD", "KHR"):
        return jsonify({"error": "currency must be USD or KHR"}), 400

    bill_number = data.get("bill_number") or make_bill_number()
    terminal    = data.get("terminal", "Cashier-01")
    is_static   = bool(data.get("static", False))
    callback    = data.get("callback")
    app_icon    = data.get("app_icon", "")

    # Convert USD amount to keep precision; KHR should be integer
    if currency == "KHR":
        amount = int(amount)

    try:
        qr_string = khqr.create_qr(
            bank_account  = BANK_ACCOUNT,
            merchant_name = MERCHANT_NAME,
            merchant_city = MERCHANT_CITY,
            amount        = amount,
            currency      = currency,
            store_label   = STORE_LABEL,
            phone_number  = PHONE_NUMBER,
            bill_number   = bill_number,
            terminal_label= terminal,
            static        = is_static,
        )
    except Exception as e:
        return jsonify({"error": f"Failed to generate QR: {str(e)}"}), 500

    md5 = khqr.generate_md5(qr_string)

    response = {
        "success"     : True,
        "qr_string"   : qr_string,
        "md5"         : md5,
        "bill_number" : bill_number,
        "amount"      : amount,
        "currency"    : currency,
    }

    # Optional deeplink
    if callback:
        try:
            deeplink = khqr.generate_deeplink(
                qr_string,
                callback   = callback,
                appIconUrl = app_icon,
            )
            response["deeplink"] = deeplink
        except Exception:
            pass  # deeplink is optional, don't fail

    # Generate base64 QR image
    try:
        qr_b64 = khqr.qr_image(qr_string, format="base64_uri")
        response["qr_image"] = qr_b64
    except Exception:
        response["qr_image"] = None  # image extras may not be installed

    return jsonify(response), 200


@app.route("/api/qr/check/<string:md5>", methods=["GET"])
def check_payment(md5):
    """
    Check if a single payment has been completed.

    Path param:
        md5   str   MD5 hash returned from /api/qr/generate

    Returns:
        paid  bool  True if payment confirmed
    """
    if not md5 or len(md5) != 32:
        return jsonify({"error": "Invalid MD5 hash"}), 400

    try:
        result = khqr.check_payment(md5)
        paid = result is not None and result.get("responseCode") == 0
        return jsonify({"success": True, "md5": md5, "paid": paid, "detail": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/qr/check-bulk", methods=["POST"])
def check_bulk():
    """
    Check multiple payment statuses at once.

    Body (JSON):
        md5_list  list[str]  List of MD5 hashes (max 50)

    Returns:
        paid_list  list[str]  MD5 hashes that are confirmed paid
    """
    data = request.get_json(force=True) or {}
    md5_list = data.get("md5_list", [])

    if not isinstance(md5_list, list) or len(md5_list) == 0:
        return jsonify({"error": "md5_list must be a non-empty array"}), 400
    if len(md5_list) > 50:
        return jsonify({"error": "md5_list cannot exceed 50 items"}), 400

    try:
        paid_list = khqr.check_bulk_payments(md5_list)
        return jsonify({"success": True, "paid_list": paid_list or []})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/payment/<string:md5>", methods=["GET"])
def get_payment(md5):
    """
    Get full transaction details for a payment.

    Path param:
        md5   str   MD5 hash of the transaction

    Returns:
        Full payment object from Bakong API
    """
    if not md5 or len(md5) != 32:
        return jsonify({"error": "Invalid MD5 hash"}), 400

    try:
        info = khqr.get_payment(md5)
        return jsonify({"success": True, "payment": info})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── Error handlers ───────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"error": "Method not allowed"}), 405


@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error"}), 500


# ─── Entry point (local dev only) ─────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, port=5000)
