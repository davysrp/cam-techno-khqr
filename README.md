# Bakong KHQR Payment API 🇰🇭

A **Flask REST API** for generating and checking **Bakong KHQR** payment QR codes, ready for cPanel shared hosting deployment.

---

## 📁 Project Structure

```
bakong-api/
├── app.py               ← Main Flask application
├── passenger_wsgi.py    ← cPanel WSGI entry point (DO NOT rename)
├── requirements.txt     ← Python dependencies
├── .htaccess            ← Apache rewrite rules
└── README.md
```

---

## ⚙️ Prerequisites

1. A cPanel hosting account with **Setup Python App** support
2. A **Bakong Developer Token** — register at [https://bakong.nbc.gov.kh](https://bakong.nbc.gov.kh)
3. Your **Bakong account ID** (e.g. `yourname@aclb` — found in the Bakong mobile app under Profile)

---

## 🚀 cPanel Deployment Steps

### Step 1 — Create a Subdomain (optional but recommended)
- Go to cPanel → **Domains** → **Create a New Domain**
- Example: `api.yourdomain.com`

### Step 2 — Set Up the Python App
- Go to cPanel → **Software** → **Setup Python App**
- Click **Create Application** and fill in:
  | Field | Value |
  |---|---|
  | Python version | 3.11 (or latest available) |
  | Application root | `bakong-api` |
  | Application URL | Your domain/subdomain |
  | Application startup file | `passenger_wsgi.py` |
  | Application entry point | `application` |

- Click **Create**

### Step 3 — Upload Files
Upload all project files to `/home/<cpanel_user>/bakong-api/` using:
- cPanel **File Manager**, or
- FTP client (FileZilla, etc.)

### Step 4 — Set Environment Variables
In the Python App settings, add these **Environment Variables**:

| Name | Value |
|---|---|
| `BAKONG_TOKEN` | Your Bakong developer JWT token |
| `BANK_ACCOUNT` | `yourname@bank` (e.g. `john@aclb`) |
| `MERCHANT_NAME` | Your business name |
| `MERCHANT_CITY` | `Phnom Penh` |
| `PHONE_NUMBER` | `855XXXXXXXXX` |
| `STORE_LABEL` | Your store name |

### Step 5 — Install Dependencies
- In the Python App panel, copy the **virtual environment activation command**
- Open cPanel **Terminal** and run:
```bash
# Activate venv (paste command from cPanel)
source /home/<user>/virtualenv/bakong-api/3.11/bin/activate

# Install packages
pip install -r /home/<user>/bakong-api/requirements.txt
```

Or use the **Run Pip Install** button in the Python App UI (uploads requirements.txt first).

### Step 6 — Restart the App
Click **Restart** in the Python App panel. Your API is live! 🎉

---

## 📡 API Reference

### `GET /`
Returns API info and available endpoints.

---

### `POST /api/qr/generate`
Generate a new KHQR payment QR code.

**Request body (JSON):**
```json
{
  "amount": 5.00,
  "currency": "USD",
  "bill_number": "INV-2024-001",
  "terminal": "Cashier-01",
  "static": false,
  "callback": "https://yoursite.com/payment/success"
}
```

**Response:**
```json
{
  "success": true,
  "qr_string": "00020101021229...",
  "md5": "a7121ca103c...eb3671b9601a6",
  "bill_number": "INV-2024-001",
  "amount": 5.00,
  "currency": "USD",
  "qr_image": "data:image/png;base64,...",
  "deeplink": "https://bakong.page.link/..."
}
```

---

### `GET /api/qr/check/<md5>`
Check if a payment has been completed.

**Response:**
```json
{
  "success": true,
  "md5": "a7121ca103c...",
  "paid": true,
  "detail": { ... }
}
```

---

### `POST /api/qr/check-bulk`
Check up to 50 payments at once.

**Request:**
```json
{
  "md5_list": ["abc123...", "def456...", "ghi789..."]
}
```

**Response:**
```json
{
  "success": true,
  "paid_list": ["abc123..."]
}
```

---

### `GET /api/payment/<md5>`
Get full transaction details.

**Response:**
```json
{
  "success": true,
  "payment": {
    "hash": "...",
    "fromAccountId": "sender@bank",
    "toAccountId": "yourname@bank",
    "currency": "USD",
    "amount": 5.00,
    "createdDateMs": 1739953000,
    "acknowledgedDateMs": 1739953010
  }
}
```

---

## 💡 Frontend Integration Example

```javascript
// 1. Generate QR
const res = await fetch('https://api.yourdomain.com/api/qr/generate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ amount: 5.00, currency: 'USD' })
});
const { qr_image, md5, bill_number } = await res.json();

// 2. Display QR image
document.getElementById('qr').src = qr_image;

// 3. Poll for payment (every 5 seconds)
const poll = setInterval(async () => {
  const check = await fetch(`https://api.yourdomain.com/api/qr/check/${md5}`);
  const { paid } = await check.json();
  if (paid) {
    clearInterval(poll);
    alert('Payment confirmed!');
  }
}, 5000);
```

---

## 🔒 Security Tips

- Keep `BAKONG_TOKEN` in environment variables, never hard-code it
- Add API key middleware if this API is public-facing
- Enable HTTPS on your cPanel domain (free via Let's Encrypt in cPanel)
- Consider rate limiting with `flask-limiter` for production

---

## 📦 Local Development

```bash
pip install -r requirements.txt
export BAKONG_TOKEN="your_token_here"
export BANK_ACCOUNT="yourname@bank"
export MERCHANT_NAME="My Business"
python app.py
# API runs at http://localhost:5000
```
