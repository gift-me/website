# GiftMe — How payments work

This document explains what happens when someone taps **Gift** on a gift or wishlist page: how we keep it fast, safe, and stable, what limits apply, and what messages people see when something goes wrong.

---

## The journey in plain English

1. **Someone picks a gift** and fills in their M-Pesa number (and optional message).
2. **They tap Gift** — we immediately **save a payment record** with status **`pending`**. Nothing is final yet.
3. **We ask Safaricom** to send an STK push (the M-Pesa prompt on their phone).
4. **They enter their PIN** on the phone (or cancel).
5. **Safaricom tells us the result** in one of two ways:
   - **Callback** (primary): Safaricom POSTs to our server → we mark the payment **completed** or **failed**.
   - **Status check** (backup): While the page shows “Processing…”, the browser checks every few seconds. If the callback is slow, we optionally ask Safaricom directly (only after a short wait, and not too often).
6. **If completed** — the gift is recorded for the recipient and the success screen appears (with optional WhatsApp share).
7. **If failed or cancelled** — the payment stays or moves to **failed**; the person can try again.

**Important:** Until Safaricom confirms success, the payment is **`pending`**. We do not treat it as money received.

```
Tap Gift → Record created (pending) → STK on phone → Safaricom callback
                                              ↓
                                    completed / failed
```

---

## What we store when someone taps Gift

| When | Status | Meaning |
|------|--------|---------|
| Right after tap, before phone prompt | `pending` | “We’ve started this payment; waiting for M-Pesa.” |
| Safaricom confirms success | `completed` | Money received; gift is created. |
| User cancelled, timeout, or error | `failed` | No gift; they can retry. |

Each payment gets a unique **reference** (12 characters) sent to M-Pesa so we can match callbacks to the right record.

---

## Making it feel seamless and fast

| What we do | Why it helps |
|------------|--------------|
| **Save `pending` immediately** | User gets a payment ID right away; the UI can show “Check your phone” without waiting for Safaricom. |
| **Browser polling** | Page updates automatically every ~2.5 seconds for up to 2 minutes — no manual refresh needed. |
| **Safaricom callback** | Usually the fastest path to `completed`; no need to wait for the next poll. |
| **Backup status check** | If callback is delayed, we query Safaricom — but only after **25 seconds** and at most once every **20 seconds** per payment (avoids hammering their API). |
| **Cached M-Pesa login token** | We reuse Safaricom’s access token (~55 minutes) so every gift doesn’t re-authenticate from scratch. |
| **Idempotency key** | If someone double-taps Gift or the network retries, we return the **same** pending payment instead of creating duplicates. |

---

## Security and abuse prevention

| Measure | What it does |
|---------|----------------|
| **CSRF protection** | Gift requests from the website must include a valid site token (stops random sites from starting payments on your users’ behalf). |
| **Rate limits** | Caps how many STK prompts can be started from one connection, one phone number, or one page (see below). |
| **Pending payment cap** | Stops someone from stacking many unpaid prompts on the same page and same number. |
| **Database locking on completion** | When Safaricom says “paid”, we lock that row so the same payment can’t be completed twice if callback and polling arrive together. |
| **Duplicate receipt check** | If the same M-Pesa receipt appears twice, we only complete once. |
| **Callback always acknowledged** | We always reply “Accepted” to Safaricom so they don’t retry callbacks endlessly. |
| **Redis optional but recommended** | Rate limits and token cache work across restarts and multiple app instances; if Redis is down, limits still work locally but won’t sync across servers. |
| **Graceful cache failures** | If Redis errors, payments still work — limits may be softer until Redis is back. |

---

## How many gift requests can we handle?

These are **configured limits** (defaults in `.env`). They protect users and Safaricom, not “maximum server capacity.”

| Setting | Default | Plain English |
|---------|---------|---------------|
| `STK_IP_LIMIT` | 10 | Max **new** gift attempts from the **same internet connection** in… |
| `STK_IP_WINDOW` | 60 seconds | …this window (usually **10 per minute per Wi‑Fi/café IP**). |
| `STK_PHONE_LIMIT` | 5 | Max attempts from the **same M-Pesa number** in… |
| `STK_PHONE_WINDOW` | 3600 seconds | …one hour (**5 per hour per phone**). |
| `STK_MAX_PENDING_PER_PHONE_PROFILE` | 3 | Max **unfinished** payments for the same number on **one person’s gift page**. |
| `STK_PROFILE_LIMIT` | 100 | Max gift attempts on **one gift/wishlist page** in… |
| `STK_PROFILE_WINDOW` | 3600 seconds | …one hour (**100 per hour per page** — protects viral traffic). |
| `PAYMENT_PENDING_EXPIRY_MINUTES` | 15 | Pending payments older than this are auto-marked **failed**. |
| `PLATFORM_FEE_PERCENT` | 10 | House fee percentage on each gift (from env). |
| `PLATFORM_FEE_CAP` | 800 | Max house fee in KES per gift (from env). |
| `STK_QUERY_MIN_AGE_SECONDS` | 25 | Wait at least this long before asking Safaricom “did they pay?” during polling. |

### Examples

- **Café Wi‑Fi:** 10 friends can start a gift within a minute. The 11th person on that same Wi‑Fi sees: *“Too many payment attempts. Please wait a minute and try again.”*
- **One phone number:** Same number can start 5 gifts in an hour across the whole site. The 6th sees: *“Too many payment attempts for this number. Please try again later.”*
- **Same gift page:** If `0712345678` already has 3 M-Pesa prompts waiting on **Amina’s page**, a 4th attempt sees: *“You already have pending payments on this page. Complete them on your phone or wait a few minutes.”*
- **Viral gift page:** If Amina’s page gets 100+ gift attempts in an hour (e.g. TikTok spike), new attempts see: *“This page is receiving a lot of gifts right now. Please try again in a few minutes.”* Verified users can be given higher limits later.
- **Stale pending:** If someone tapped Gift but never paid, the payment moves to **failed** after **15 minutes** with message *“Payment timed out. Please try again.”*

---

## Messages people see (no jargon)

### When starting a gift (tap Gift)

| Situation | Message shown |
|-----------|-----------------|
| Invalid phone (not `07XXXXXXXX`) | **Enter a valid M-Pesa number.** |
| Bad or missing amount | **Enter a valid amount and try again.** |
| Gift page doesn’t exist | **Page not found.** |
| Broken request body | **Invalid request.** |
| Too many tries from same connection | **Too many payment attempts. Please wait a minute and try again.** |
| Too many tries from same M-Pesa number | **Too many payment attempts for this number. Please try again later.** |
| Too many unpaid prompts on this page | **You already have pending payments on this page. Complete them on your phone or wait a few minutes.** |
| Too many attempts on this gift page (viral spike) | **This page is receiving a lot of gifts right now. Please try again in a few minutes.** |
| Pending payment expired (15+ min) | **Payment timed out. Please try again.** |
| Safaricom didn’t accept the prompt | **STK Push failed to start.** (or Safaricom’s own short message if they provide one) |
| Network / browser issue | **Network error. Please try again.** |
| Anything else unexpected | **Could not start payment.** |

### While waiting on the phone

| Situation | Message shown |
|-----------|-----------------|
| STK sent successfully | **STK prompt sent. Check your phone to complete payment.** (loading state on page) |
| Still waiting after ~2 minutes | **Payment is taking longer than expected. If you paid, refresh the page.** |
| Safaricom said no / user cancelled | **Payment failed. Please try again.** (or Safaricom’s reason in plain text when available) |

### After success

- Success screen with option to **Share on WhatsApp**.

---

## Keeping the system from crashing

| Approach | How it helps |
|----------|----------------|
| **Pending first, confirm later** | Heavy work (marking completed, creating the gift) only runs once Safaricom confirms — not on every button click. |
| **Throttled Safaricom queries** | Status checks are spaced out so polling thousands of users doesn’t flood Daraja. |
| **Short DB transactions** | Completing or failing a payment uses a locked row and finishes quickly. |
| **Idempotency** | Retries don’t multiply database rows or STK pushes for the same intent. |
| **Rate limits** | Stops abuse that could overload the app or Safaricom. |
| **Cache fails open** | Redis problems don’t take down payments entirely. |
| **Always accept callbacks** | Prevents Safaricom retry storms from duplicate processing attempts. |

**Production note:** Run with **PostgreSQL**, **Redis**, and multiple **Gunicorn/uWSGI workers** for real traffic. SQLite + single dev server (used in local load tests) is not a production target.

---

## Load test results (local, June 2026)

We ran an automated load test on the **development** setup (SQLite, single process, **M-Pesa mocked** so Safaricom wasn’t called). Script: `scripts/payment_load_test.py`.

| Test | Result |
|------|--------|
| **50 concurrent gift starts, unique IPs** | **50/50 succeeded** in ~5.1s (~**10 successful starts/sec**) |
| **20 concurrent gift starts, same IP** | **~6–10 succeeded**, rest **rate limited** (confirms **10/min per IP** cap) |
| **100 status checks on one payment** | **~81 requests/sec**, typical wait **~12 ms** per check |
| **Typical gift-start latency (under load)** | Median **~50–3300 ms** depending on concurrency (SQLite serializes writes) |

### What this means in practice

| Layer | Rough capacity (current dev config) |
|-------|-------------------------------------|
| **Configured abuse limits** | **10 starts/min/IP**, **5 starts/hour/phone**, **3 pending/phone/page** |
| **Status polling endpoint** | **~80+ checks/sec** per server (lightweight reads) |
| **Gift start endpoint (no rate limit hit)** | **~10 writes/sec** on dev SQLite; **higher with PostgreSQL + Redis + workers** |
| **Real Safaricom limit** | Safaricom’s own STK limits apply on top — production throughput is often **bounded by Daraja**, not our app |

Re-run the test anytime:

```bash
python scripts/payment_load_test.py
```

---

## API endpoints (for developers)

| Method | Path | Role |
|--------|------|------|
| `POST` | `/api/mpesa/stk-push/` | Start gift → creates **`pending`** payment, sends STK |
| `GET` | `/api/mpesa/status/<payment_id>/` | Poll payment status |
| `POST` | `/api/mpesa/callback/` | Safaricom webhook (not called by browsers) |

---

## Environment variables (payments)

See `.env.example` for full list. Key ones:

```env
REDIS_URL=redis://127.0.0.1:6379/1
MPESA_CALLBACK_URL=https://your-domain.com/api/mpesa/callback/
STK_QUERY_MIN_AGE_SECONDS=25
STK_IP_LIMIT=10
STK_IP_WINDOW=60
STK_PHONE_LIMIT=5
STK_PHONE_WINDOW=3600
STK_MAX_PENDING_PER_PHONE_PROFILE=3
STK_PROFILE_LIMIT=100
STK_PROFILE_WINDOW=3600
PAYMENT_PENDING_EXPIRY_MINUTES=15
PLATFORM_FEE_PERCENT=10
PLATFORM_FEE_CAP=800
```

---

## Related code

| Area | Location |
|------|----------|
| STK + callback views | `birthdays/mpesa_views.py` |
| Payment flow + pending/completed | `birthdays/payment_service.py` |
| Rate limits | `birthdays/payment_limits.py` |
| Pending expiry | `birthdays/payment_expiry.py` |
| Idempotency | `birthdays/payment_idempotency.py` |
| Safaricom client | `birthdays/mpesa.py` |
| Browser modal + polling | `static/js/contribute-modal.js` |
| Load test | `scripts/payment_load_test.py` |
