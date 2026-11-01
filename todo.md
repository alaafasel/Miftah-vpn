# MIFTAH VPN — خطة إكمال المشروع

## 1. Backend — استكمال الـ API
- [x] إضافة نماذج `XrayServer` و`XrayServerUser` و`Device.selected_proxy_id`
- [x] Migration جديدة `0002_xray_manager`
- [x] إضافة `POST /api/v1/devices/unbind` و`GET /api/v1/devices/me`
- [x] إضافة حفظ اختيار البروكسي `POST /api/v1/proxies/select` وتطبيقه على config/current
- [x] إدارة الاشتراكات `admin/subscriptions`
- [x] إدارة صلاحيات البروكسي لكل كود `admin/proxies/{id}/access`
- [x] Xray Manager API `admin/xray/*` + عميل الوكيل
- [x] التحقق من JSON عبر `xray run -test` عند توفر الملف التنفيذي
- [x] تحديث `main.py` و`requirements.txt`

## 2. Xray Manager Agent
- [x] `xray-manager/agent.py` (FastAPI وكيل على سيرفر Xray)
- [x] تثبيت systemd + سكربت install
- [x] توثيق

## 3. لوحة الإدارة
- [x] صفحة الاشتراكات
- [x] صفحة Xray Manager
- [x] ربط البروكسيات بالأكواد
- [x] تحديث القائمة والتنقل

## 4. تطبيق Android (Kotlin + Compose)
- [x] هيكل Gradle كامل
- [x] هوية الجهاز عبر Android Keystore
- [x] تخزين مشفّر AES-GCM
- [x] عميل API + نماذج
- [x] شاشات: البداية، التفعيل، الرئيسية، البروكسي، الحساب
- [x] XrayCore + Tun2Socks + VpnService
- [x] patcher للـ JSON (UUID + proxy address)
- [x] أيقونات وموارد
- [x] سكربت بناء المكتبات الأصلية `native/build-native.sh`

## 5. التوثيق والتحقق
- [ ] README رئيسي
- [ ] docs/DEPLOY.md
- [ ] docs/API.md
- [ ] docs/ANDROID_BUILD.md
- [ ] docs/SECURITY.md
- [x] فحص Python syntax + JS syntax
- [ ] اختبارات وحدات للدوال النقية

## 6. النشر والتحقق العملي
- [ ] تثبيت Docker على سيرفر التحكم
- [ ] `docker compose up -d` + `alembic upgrade head`
- [ ] إنشاء حساب المدير
- [ ] التحقق من `/health` و`/health/db`
- [ ] فتح لوحة MIFTAH CONTROL
