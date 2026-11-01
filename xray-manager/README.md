# MIFTAH Xray Manager Agent

وكيل صغير يعمل على سيرفر Xray المنفصل، ويُدار بالكامل من لوحة MIFTAH CONTROL.

## التثبيت
```bash
sudo AGENT_TOKEN="$(openssl rand -hex 32)" ./install.sh
```

## الأوامر المتاحة
- `GET /health` — حالة الخدمة وإصدار Xray.
- `GET /status` — تفاصيل الإعداد الحالي.
- `POST /config/validate` — التحقق من JSON عبر `xray run -test`.
- `POST /config/apply` — كتابة الإعداد وإعادة تشغيل الخدمة (مع نسخة احتياطية).
- `POST /users/sync` — مزامنة قائمة UUIDs مع inbounds.
- `POST /service/restart` — إعادة تشغيل Xray.

كل الطلبات تتطلب الترويسة `X-Agent-Token`.

## الأمان
- الوكيل يستمع على `127.0.0.1` فقط.
- يجب تعريضه عبر Caddy مع HTTPS ومسار خاص، أو عبر WireGuard/SSH tunnel.
- لا ينفّذ أي أمر شل من العميل؛ الأوامر ثابتة ومحصورة.
