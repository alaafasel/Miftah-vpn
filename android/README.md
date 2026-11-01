# MIFTAH VPN — تطبيق المشترك (Android)

تطبيق Kotlin + Jetpack Compose، الحزمة `com.miftah.vpn`.
**الـ APK فارغ قبل التفعيل:** لا UUID، لا عنوان سيرفر، لا JSON، لا قائمة بروكسيات.
كل شيء يُجلب من الـ API بعد التحقق من كود التفعيل على السيرفر.

## المتطلبات

- JDK 17
- Android SDK: platform 35 + build-tools 35
- Android NDK r26+ و CMake 3.22 (لبناء `libmiftah-tun.so`)
- Go 1.22+ (لبناء AAR الخاص بـ Xray عبر gomobile)

## 1. ضبط عنوان الـ API

في `gradle.properties`:

```properties
miftah.apiBase=https://YOUR_DOMAIN:8443/
```

أو عند البناء:

```bash
./gradlew assembleRelease -Pmiftah.apiBase=https://vpn.example.com/
```

يجب أن يكون العنوان **HTTPS**؛ التطبيق يمنع الـ cleartext
(`usesCleartextTraffic=false` + `network_security_config.xml`).

## 2. بناء المكتبات الأصلية

```bash
cd native
export ANDROID_HOME=$HOME/Android/Sdk
./build-native.sh
```

الناتج:

- `app/libs/libXray.aar` — Xray-core (gomobile bind لـ `native/xraymobile`)
- `app/src/main/jniLibs/arm64-v8a/libmiftah-tun.so` — hev-socks5-tunnel JNI

بدون هذين الملفين يُبنى التطبيق لكنه يفشل عند الاتصال برسالة واضحة
(`Xray core not bundled`). هذا مقصود حتى لا يُشحن APK ناقص.

## 3. البناء

```bash
./gradlew assembleDebug     # app/build/outputs/apk/debug/app-debug.apk
./gradlew assembleRelease   # يحتاج keystore
```

توقيع الإصدار — أنشئ `keystore.properties` (لا يُرفع للمستودع):

```properties
storeFile=/absolute/path/miftah-release.jks
storePassword=...
keyAlias=miftah
keyPassword=...
```

وأضف في `app/build.gradle.kts` داخل `android { }`:

```kotlin
signingConfigs {
    create("release") {
        val props = java.util.Properties().apply {
            file("../keystore.properties").inputStream().use { load(it) }
        }
        storeFile = file(props.getProperty("storeFile"))
        storePassword = props.getProperty("storePassword")
        keyAlias = props.getProperty("keyAlias")
        keyPassword = props.getProperty("keyPassword")
    }
}
buildTypes { getByName("release") { signingConfig = signingConfigs.getByName("release") } }
```

## 4. مسار التشغيل

1. `SplashScreen` — شعار مفتاح + فحص الترخيص.
2. `ActivationScreen` — إدخال الكود، الإرسال إلى `POST /api/v1/licenses/activate`
   مع المفتاح العام لجهاز Keystore. لا تحقق محلي إطلاقاً.
3. `HomeScreen` — اتصال/فصل، الحالة، البروكسي المحدد، الأيام المتبقية، حالة الترخيص.
4. `ProxiesScreen` — قائمة يحددها المدير فقط، اختيار واحد يُحفظ على السيرفر وعلى الجهاز.
5. `AccountScreen` — تواريخ الاشتراك، معلومات الجهاز، فك الارتباط.

## 5. آلية الاتصال

```
VpnService.establish()  ->  TUN fd
        |
        v
hev-socks5-tunnel (libmiftah-tun.so)  ->  127.0.0.1:10808
        |
        v
Xray-core (libXray.aar)  ->  outbound proxyfb -> address المختار
```

- يُطبَّق تعديلان فقط على JSON قبل التشغيل: استبدال `{{UUID}}` (احتياطي)،
  وتغيير `outbounds[tag=proxyfb].settings.servers[0].address`.
- يُضاف inbound محلي `socks 127.0.0.1:10808` إذا لم يكن موجوداً، لأن tun2socks يحتاجه.
- التطبيق نفسه مستثنى من النفق (`addDisallowedApplication`) لمنع حلقة التوجيه.
- تحديث الإعداد: `GET /api/v1/config/version` ثم تحميل النسخة الجديدة فقط عند اختلافها.

## 6. الأمان

- مفتاح EC P-256 غير قابل للتصدير داخل Android Keystore؛ يُرسل المفتاح العام فقط.
- التوكن والـ JSON والبروكسي في `EncryptedSharedPreferences` (AES256-SIV/GCM).
- `allowBackup=false` واستثناء كل الملفات من النسخ الاحتياطي.
- لا أسرار إدارية ولا UUIDs في الـ APK.
