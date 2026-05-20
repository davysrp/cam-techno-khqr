"""
Bakong KHQR Payment API
Flask REST API — No Bakong token required for QR generation.
Token only needed for payment checking (check_payment uses Bakong Open API).
"""

import os
import uuid
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from bakong_khqr import KHQR

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

@app.before_request
def handle_options():
    if request.method == "OPTIONS":
        res = Response()
        res.headers["Access-Control-Allow-Origin"]  = "*"
        res.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        res.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Merchant-ID"
        return res, 200

# ─── Merchant Account List ─────────────────────────────────────────────────────
# No token needed for QR generation.
# Token only needed for check_payment / get_payment (Bakong Open API calls).
MERCHANTS = {
    "ct": {
        "name"         : "CT Services",
        "bank_account" : "sophath_9999@aclb",
        "merchant_name": "CT Services",
        "merchant_city": "Phnom Penh",
        "phone_number" : "85599330067",
        "store_label"  : "CT Services",
    },
    "chatkh": {
        "name"         : "ChatKH by Bunthorn",
        "bank_account" : "chhangbunthornkh@aclb",
        "merchant_name": "ChatKH by Bunthorn",
        "merchant_city": "Phnom Penh",
        "phone_number" : "855962018555",
        "store_label"  : "ChatKH by Bunthorn",
    },
    "katanamovie": {
        "name"         : "KATANA MOVIE",
        "bank_account" : "pharith_pat@bkrt",
        "merchant_name": "KATANA MOVIE",
        "merchant_city": "Phnom Penh",
        "phone_number" : "855965880459",
        "store_label"  : "KATANA MOVIE",
    },
    "iskillbiz": {
        "name"         : "iSkillbiz by Veasna",
        "bank_account" : "veasna_peach1@aclb",
        "merchant_name": "iSkillbiz by Veasna",
        "merchant_city": "Phnom Penh",
        "phone_number" : "85517789499",
        "store_label"  : "iSkillbiz by Veasna",
    },
    # ─── Add more merchants below ───
    # "newmerchant": {
    #     "name"         : "New Merchant",
    #     "bank_account" : "name@bank",
    #     "merchant_name": "New Merchant",
    #     "merchant_city": "Phnom Penh",
    #     "phone_number" : "855XXXXXXXXX",
    #     "store_label"  : "New Merchant",
    # },
}

# ─── Helpers ──────────────────────────────────────────────────────────────────

def make_bill_number():
    return "TRX" + uuid.uuid4().hex[:10].upper()

def get_merchant(merchant_id):
    return MERCHANTS.get(merchant_id)

# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
def index():
    merchant_list = {
        mid: {
            "name"         : m["name"],
            "bank_account" : m["bank_account"],
            "merchant_name": m["merchant_name"],
            "merchant_city": m["merchant_city"],
            "store_label"  : m["store_label"],
        }
        for mid, m in MERCHANTS.items()
    }
    return jsonify({
        "service"        : "Bakong KHQR Payment API",
        "version"        : "3.0.0",
        "status"         : "running",
        "total_merchants": len(MERCHANTS),
        "merchants"      : merchant_list,
        "endpoints"      : {
            "POST /api/qr/generate"    : "Generate QR — pass merchant_id in body",
            "GET  /api/qr/check/<md5>" : "Check payment — pass merchant_id as query param",
            "POST /api/qr/check-bulk"  : "Check multiple payments at once",
            "GET  /api/payment/<md5>"  : "Get full transaction info",
            "GET  /api/merchants"      : "List all merchants",
            "GET  /api/health"         : "Health check",
        }
    })


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "total_merchants": len(MERCHANTS)})


@app.route("/api/merchants", methods=["GET"])
def list_merchants():
    """List all available merchant accounts."""
    merchant_list = {
        mid: {
            "name"         : m["name"],
            "bank_account" : m["bank_account"],
            "merchant_name": m["merchant_name"],
            "merchant_city": m["merchant_city"],
            "store_label"  : m["store_label"],
        }
        for mid, m in MERCHANTS.items()
    }
    return jsonify({"success": True, "merchants": merchant_list})


@app.route("/api/qr/generate", methods=["POST"])
def generate_qr():
    """
    Generate a Bakong KHQR payment QR code. No token required.

    Body (JSON):
        merchant_id  str    required  e.g. "ct", "chatkh", "katanamovie", "iskillbiz"
        amount       float  required  Payment amount
        currency     str    optional  "USD" or "KHR" (default: USD)
        bill_number  str    optional  Custom reference — auto-generated if omitted
        terminal     str    optional  Terminal/cashier label
        static       bool   optional  True for static QR (default: false)
        callback     str    optional  Deeplink callback URL
        app_icon     str    optional  App icon URL for deeplink
    """
    data = request.get_json(force=True) or {}

    # Resolve merchant
    merchant_id = data.get("merchant_id") or request.headers.get("X-Merchant-ID")
    if not merchant_id:
        return jsonify({
            "error"              : "merchant_id is required",
            "available_merchants": list(MERCHANTS.keys())
        }), 400

    merchant = get_merchant(merchant_id)
    if not merchant:
        return jsonify({
            "error"              : f"Merchant '{merchant_id}' not found",
            "available_merchants": list(MERCHANTS.keys())
        }), 404

    # Validate amount
    amount = data.get("amount")
    if amount is None:
        return jsonify({"error": "amount is required"}), 400
    try:
        amount = float(amount)
        if amount <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"error": "amount must be a positive number"}), 400

    # Validate currency
    currency = str(data.get("currency", "USD")).upper()
    if currency not in ("USD", "KHR"):
        return jsonify({"error": "currency must be USD or KHR"}), 400

    bill_number = data.get("bill_number") or make_bill_number()
    terminal    = data.get("terminal", "Cashier-01")
    is_static   = bool(data.get("static", False))
    callback    = data.get("callback")
    app_icon    = data.get("app_icon", "")

    # KHR must be integer
    if currency == "KHR":
        amount = int(amount)

    try:
        # No token needed for QR generation — pass empty string
        khqr      = KHQR("")
        qr_string = khqr.create_qr(
            bank_account   = merchant["bank_account"],
            merchant_name  = merchant["merchant_name"],
            merchant_city  = merchant["merchant_city"],
            amount         = amount,
            currency       = currency,
            store_label    = merchant["store_label"],
            phone_number   = merchant["phone_number"],
            bill_number    = bill_number,
            terminal_label = terminal,
            static         = is_static,
        )
    except Exception as e:
        return jsonify({"error": f"Failed to generate QR: {str(e)}"}), 500

    md5 = khqr.generate_md5(qr_string)

    response = {
        "success"    : True,
        "merchant_id": merchant_id,
        "merchant"   : merchant["name"],
        "qr_string"  : qr_string,
        "md5"        : md5,
        "bill_number": bill_number,
        "amount"     : amount,
        "currency"   : currency,
    }

    # Optional deeplink
    if callback:
        try:
            response["deeplink"] = khqr.generate_deeplink(
                qr_string, callback=callback, appIconUrl=app_icon
            )
        except Exception:
            pass

    # QR image as base64
    try:
        response["qr_image"] = khqr.qr_image(qr_string, format="base64_uri")
    except Exception:
        response["qr_image"] = None

    return jsonify(response), 200


@app.route("/api/qr/generate-dynamic", methods=["POST"])
def generate_qr_dynamic():
    """
    Generate a Bakong KHQR QR code for any merchant without pre-registration.

    Body (JSON):
        bank_account   str    required  e.g. "name@bank"
        merchant_name  str    required  Display name of the merchant
        merchant_city  str    optional  Default: "Phnom Penh"
        phone_number   str    optional  e.g. "855XXXXXXXXX"
        store_label    str    optional  Defaults to merchant_name
        amount         float  required  Payment amount (positive)
        currency       str    optional  "USD" or "KHR" (default: USD)
        bill_number    str    optional  Auto-generated if omitted
        terminal       str    optional  Terminal/cashier label
        static         bool   optional  True for static QR (default: false)
        callback       str    optional  Deeplink callback URL
        app_icon       str    optional  App icon URL for deeplink
    """
    data = request.get_json(force=True) or {}

    bank_account = data.get("bank_account", "").strip()
    if not bank_account:
        return jsonify({"error": "bank_account is required"}), 400

    merchant_name = data.get("merchant_name", "").strip()
    if not merchant_name:
        return jsonify({"error": "merchant_name is required"}), 400

    merchant_city = data.get("merchant_city", "Phnom Penh").strip() or "Phnom Penh"
    phone_number  = data.get("phone_number", "")
    store_label   = data.get("store_label", merchant_name).strip() or merchant_name

    amount = data.get("amount")
    if amount is None:
        return jsonify({"error": "amount is required"}), 400
    try:
        amount = float(amount)
        if amount <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"error": "amount must be a positive number"}), 400

    currency = str(data.get("currency", "USD")).upper()
    if currency not in ("USD", "KHR"):
        return jsonify({"error": "currency must be USD or KHR"}), 400

    if currency == "KHR":
        amount = int(amount)

    bill_number = data.get("bill_number") or make_bill_number()
    terminal    = data.get("terminal", "Cashier-01")
    is_static   = bool(data.get("static", False))
    callback    = data.get("callback")
    app_icon    = data.get("app_icon", "")

    try:
        khqr      = KHQR("")
        qr_string = khqr.create_qr(
            bank_account   = bank_account,
            merchant_name  = merchant_name,
            merchant_city  = merchant_city,
            amount         = amount,
            currency       = currency,
            store_label    = store_label,
            phone_number   = phone_number,
            bill_number    = bill_number,
            terminal_label = terminal,
            static         = is_static,
        )
    except Exception as e:
        return jsonify({"error": f"Failed to generate QR: {str(e)}"}), 500

    md5 = khqr.generate_md5(qr_string)

    response = {
        "success"      : True,
        "bank_account" : bank_account,
        "merchant_name": merchant_name,
        "merchant_city": merchant_city,
        "store_label"  : store_label,
        "qr_string"    : qr_string,
        "md5"          : md5,
        "bill_number"  : bill_number,
        "amount"       : amount,
        "currency"     : currency,
    }

    if callback:
        try:
            response["deeplink"] = khqr.generate_deeplink(
                qr_string, callback=callback, appIconUrl=app_icon
            )
        except Exception:
            pass

    try:
        response["qr_image"] = khqr.qr_image(qr_string, format="base64_uri")
    except Exception:
        response["qr_image"] = None

    return jsonify(response), 200


@app.route("/api/qr/check/<string:md5>", methods=["GET"])
def check_payment(md5):
    """
    Check if a payment has been completed.
    Requires bakong_token as query param (needed for Bakong Open API call).

    Path:   /api/qr/check/<md5>
    Query:  merchant_id=ct  &  bakong_token=eyJ...  (optional if not set in ENV)
    """
    if not md5 or len(md5) != 32:
        return jsonify({"error": "Invalid MD5 hash"}), 400

    merchant_id = request.args.get("merchant_id") or request.headers.get("X-Merchant-ID")
    if not merchant_id:
        return jsonify({"error": "merchant_id is required as query param"}), 400

    merchant = get_merchant(merchant_id)
    if not merchant:
        return jsonify({"error": f"Merchant '{merchant_id}' not found"}), 404

    # Token needed only for checking payment status via Bakong Open API
    token = request.args.get("bakong_token") or os.environ.get("BAKONG_TOKEN", "")

    try:
        khqr   = KHQR(token)
        result = khqr.check_payment(md5)
        paid   = result is not None and result.get("responseCode") == 0
        return jsonify({
            "success"    : True,
            "merchant_id": merchant_id,
            "md5"        : md5,
            "paid"       : paid,
            "detail"     : result
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/qr/check-bulk", methods=["POST"])
def check_bulk():
    """
    Check multiple payments at once (max 50).

    Body (JSON):
        merchant_id   str        required
        md5_list      list[str]  required  Max 50 hashes
        bakong_token  str        optional  Override token for this request
    """
    data        = request.get_json(force=True) or {}
    md5_list    = data.get("md5_list", [])
    merchant_id = data.get("merchant_id") or request.headers.get("X-Merchant-ID")

    if not merchant_id:
        return jsonify({"error": "merchant_id is required"}), 400

    merchant = get_merchant(merchant_id)
    if not merchant:
        return jsonify({"error": f"Merchant '{merchant_id}' not found"}), 404

    if not isinstance(md5_list, list) or len(md5_list) == 0:
        return jsonify({"error": "md5_list must be a non-empty array"}), 400
    if len(md5_list) > 50:
        return jsonify({"error": "md5_list cannot exceed 50 items"}), 400

    token = data.get("bakong_token") or os.environ.get("BAKONG_TOKEN", "")

    try:
        khqr      = KHQR(token)
        paid_list = khqr.check_bulk_payments(md5_list)
        return jsonify({
            "success"    : True,
            "merchant_id": merchant_id,
            "paid_list"  : paid_list or []
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/payment/<string:md5>", methods=["GET"])
def get_payment(md5):
    """
    Get full transaction details.

    Path:   /api/payment/<md5>
    Query:  merchant_id=ct  &  bakong_token=eyJ...  (optional)
    """
    if not md5 or len(md5) != 32:
        return jsonify({"error": "Invalid MD5 hash"}), 400

    merchant_id = request.args.get("merchant_id") or request.headers.get("X-Merchant-ID")
    if not merchant_id:
        return jsonify({"error": "merchant_id is required as query param"}), 400

    merchant = get_merchant(merchant_id)
    if not merchant:
        return jsonify({"error": f"Merchant '{merchant_id}' not found"}), 404

    token = request.args.get("bakong_token") or os.environ.get("BAKONG_TOKEN", "")

    try:
        khqr = KHQR(token)
        info = khqr.get_payment(md5)
        return jsonify({
            "success"    : True,
            "merchant_id": merchant_id,
            "payment"    : info
        })
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