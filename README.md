# AriaTunnel / HyperTunnel

یک سیستم تونل‌زنی امن، پرسرعت و سبک با پنل مدیریت تحت وب (FastAPI) برای عبور ترافیک از ایران به سرور خارج با بالاترین امنیت و کمترین تاخیر (Latency).

## ویژگی‌ها
- **تونل رمزنگاری‌شده مدرن:** پروتکل اختصاصی مبتنی بر Asyncio (TCP/UDP Multiplexing) با رمزنگاری ChaCha20/AES.
- **پنل مدیریت (Web Dashboard):** مدیریت کاربران، حجم ترافیک، تاریخ انقضا و وضعیت نودها.
- **نصب خودکار:** اسکریپت تک‌خطی برای نصب روی سرورهای ایران و خارج.
- **مقاوم در برابر فیلترینگ:** ساختار تمیز و قابل توسعه.
- **پشتیبانی از Docker:** استقرار آسان با یک دستور.

## 🚀 نصب تک‌خطی (One-Liner Install)

با یک دستور، پنل مدیریت و دیمون‌های تونل را نصب و راه‌اندازی کنید:

### ۱. نصب پنل مدیریت (روی سرور پنل / ایران)
```bash
bash <(curl -sSL https://raw.githubusercontent.com/Hosein21378/ariatunnel/master/deploy/install.sh) panel
```
پس از نصب، پنل روی پورت `8000` در دسترس خواهد بود.

### ۲. نصب سرور خارج (Server)
```bash
bash <(curl -sSL https://raw.githubusercontent.com/Hosein21378/ariatunnel/master/deploy/install.sh) server
```

### ۳. نصب سرور ایران (Client)
*(به جای IP_KHAREJ آی‌پی سرور خارج را وارد کنید)*
```bash
SERVER_HOST=<IP_KHAREJ> bash <(curl -sSL https://raw.githubusercontent.com/Hosein21378/ariatunnel/master/deploy/install.sh) client
```

---

## 🖥 اتصال سرورها از داخل پنل

1. پنل را باز کن: `http://<IP>:8000`
2. روی سرور خارج یک‌بار نصب `server` بزن — اسکریپت آخر کار `TUNNEL_SECRET=...` را چاپ می‌کند.
3. در پنل فرم **افزودن نود**: نام، IP سرور خارج، کشور و همان SECRET را وارد کن.
4. دکمه **اتصال تونل** → کلاینت روی پورت `10801` (هر نود +۱) بالا می‌آید و تونل برقرار می‌شود.
5. دکمه **قطع** → پروسهٔ تونل همان نود بسته می‌شود.

---

## ساختار پروژه
```
.
├── panel/
│   ├── main.py          # پنل مدیریت FastAPI
│   └── templates/       # قالب‌های HTML داشبورد
├── core/
│   ├── server.py        # دیتاسنتر / سرور خارج
│   └── client.py        # سرور ایران / کلاینت تونل
├── deploy/
│   └── install.sh       # اسکریپت نصب خودکار
├── Dockerfile
└── docker-compose.yml
```
