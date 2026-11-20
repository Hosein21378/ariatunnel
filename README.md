# AriaTunnel — تونل اختصاصی برای عبور ترافیک از ایران به خارج

توأمین تونل رمزنگارisé (ChaCha20-Poly1305) بین سرور ایران (ورودی) و سرور خارج (خروجی) با پنل مدیریت وب (FastAPI) و قابلیت ترانسپورت **TLS** برای مقاومت در برابر DPI و 필تر شدن.

## معماری

```
کاربران اینترنت → [سرور ایران: پورت لوکال] → [تونل TLS/TCP رمزنگار] → [سرور خارج ترکیه] → مقصد واقعی (مثل 1.1.1.1:443)
```

## استقرار سریع (تک خطی)

سرور خارج (ترکیه / خروجی):
```bash
bash <(curl -sSL https://codeload.github.com/Hosein21378/ariatunnel/tar.gz/refs/heads/master | tar xz -O deploy/install.sh) server
```

سرور ایران (ورودی) — ترانسپورت TCP (سریع، diagnosis آسان):
```bash
SERVER_HOST=206.1.97.101 bash <(curl -sSL https://codeload.github.com/Hosein21378/ariatunnel/tar.gz/refs/heads/master | tar xz -O deploy/install.sh) client
```

سرور ایران (ورودی) — ترانسپورت TLS (مثل HTTPS، DPI-resistant، مناسب برای دور زدن فیلتر):
```bash
SERVER_HOST=206.1.97.101 SERVER_PORT=443 CLIENT_TRANSPORT=tls bash <(curl -sSL https://codeload.github.com/Hosein21378/ariatunnel/tar.gz/refs/heads/master | tar xz -O deploy/install.sh) client
```

پنل مدیریت (سرور خارج یا هر سرور با IP عمومی):
```bash
bash <(curl -sSL https://codeload.github.com/Hosein21378/ariatunnel/tar.gz/refs/heads/master | tar xz -O deploy/install.sh) panel
```

## پنل مدیریت (FastAPI)

بعد از استارت پنل، به `http://<ip-panel>:8000` مراجعه کنید:

1. نود خارج را اضافه کنید (IP سرور خارج، ترانسپورت `tcp` یا `tls`، پورت لوکال، مقصد).
2. دکمه **اتصال تونل** را بزنید — کلاینت AriaTunnel روی ایران استارت می‌شود.
3. ترافیک کاربران به پورت لوکال ایران ارسال شود → از تونل TLS عبور کرده → به مقصد vraie دسترسی پیدا می‌کنند.

### ترانسپورت‌ها
| ترانسپورت | توضیح | مناسبت برای DPI |
|-----------|-------|------------------|
| `tcp` | ترمز خام (بدون TLS) | پایین — DPI می‌تواند شناسایی کند |
| `tls` | TLS بسته‌بندی شده (مثل HTTPS) | بالا — شبیه ترافیک وب عادی است |

## نکات امنیتی

- کلید مشترک (`TUNNEL_SECRET`) در `/etc/ariatunnel.secret` ذخیره می‌شود؛ هرگز در چت یا گیت‌هاب ثبت نکنید.
- برای TLS، گواهی‌نامهٔ خود amضاء (self-signed) به صورت اتوماتیک تولید می‌شود.
- تغییرات بر گزینه بازگشتی هستند (git revert / stash).

## فایل‌های پروژه

- `core/server.py` — هسته سرور خارج (پذیرش تونل، Forward به مقصد)
- `core/client.py` — هسته کلاینت ایران (پورت لوکال → تونل → خارج)
- `panel/main.py` — پنل FastAPI (مدیریت نودها، اتصال/قطع تونل)
- `panel/templates/index.html` — رابط وب مدیریت (فارسی، RTL)
- `deploy/install.sh` — نصب تک‌خطی برای server/client/panel
- `tests/selfcheck.py` — تست رله end-to-end
- `tests/panel_e2e.py` — تست پنل → نود → تونل

## گیت‌هاب

https://github.com/Hosein21378/ariatunnel (عمومی)
