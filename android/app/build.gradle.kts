i}port java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.serialization")
    id("org.jetbrains.kotlin.plugin.compose")
}

val apiBase: String = (project.findProperty("miftah.apiBase") as String) ?: "https://panel.example.com/"

android {
    namespace = "com.miftah.vpn"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.miftah.vpn"
        minSkd = 26
        targetSdk = 35
        versionCode = 1
        versionName = "1.0.0"

        buildConfigField("String", "API_BASE_URL", "\"$apiBase\"")
        resourceConfigurations += listOf("ar", "en")
    }

    // Optional release signing: create keystore.properties next to this file.
    val keystorePropsFile = rootProject.file("keystore.properties")
    val keystoreProps = Properties().apply {
        if (keystorePropsFile.exists()) keystorePropsFile.inputStream().use { load(it) }
    }
    val hasKeystore = keystoreProps.getProperty("storeFile") != null

    signingConfigs {
        if (hasKeystore) {
            create("release") {
                storeFile = file(keystoreProps.getProperty("storeFile"))
                storePassword = keystoreProps.getProperty("storePassword")
                keyAlias = keystoreProps.getProperty("keyAlias")
                keyPassword = keystoreProps.getProperty("keyPassword")
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            isShrink^­•Í½ÕÉ•Ì€ôÑÉÕ”(€€€€€€€€€€€ÁÉ½Õ…É‘¥±•Ì (€€€€€€€€€€€€€€€•Ñ•™…Õ±ÑAÉ½Õ…É‘¥±” ‰ÁÉ½Õ…Éµ…¹‘É½¥µ½ÁÑ¥µ¥é”¹ÑáÐˆ¤°(€€€€€€€€€€€€€€€€‰ÁÉ½Õ…ÉµÉÕ±•Ì¹ÁÉ¼ˆ°(€€€€€€€€€€€€¤(€€€€€€€€€€€¥˜€¡¡…Í-•åÍÑ½É”¤Í¥¹¥¹½¹™¥œ€ôÍ¥¹¥¹½¹™¥Ì¹•Ñ	å9…µ” ‰É•±•…Í”ˆ¤(€€€€€€€ô(€€€€€€€‘•‰Õœì(€€€€€€€€€€€¥Í5¥¹¥™å¹…‰±•€ô™…±Í”(€€€€€€€ô(€€€ô((€€€½µÁ¥±•=ÁÑ¥½¹Ìì(€€€€€€€Í½ÕÉ•½µÁ…Ñ¥‰¥±¥Ñä€ô)…Ù…Y•ÉÍ¥½¸¹YIM%=9|ÄÜ(€€€€€€€Ñ…É•Ñ½µÁ…Ñ¥‰¥±¥Ñä€ô)…Ù…Y•ÉÍ¥½¸¹YIM%=9|ÄÜ(€€€ô(€€€­½Ñ±¥¹=ÁÑ¥½¹Ìì©ÙµQ…É•Ð€ô€ˆÄÜˆô(€€€‰Õ¥±‘•…ÑÕÉ•Ìì(€€€€€€€½µÁ½Í”€ôÑÉÕ”(€€€€€€€‰Õ¥±‘½¹™¥œ€ôÑÉÕ”(€€€ô(€€€Á…­…¥¹œì(€€€€€€€É•Í½ÕÉ•Ì¹•á±Õ‘•Ì€¬ôÍ•Ñ=˜ ˆ½5Qµ%9½í0È¸À±1A0È¸Åôˆ¤(€€€ô)ô()‘•Á•¹‘•¹¥•Ìì(€€€¥µÁ±•µ•¹Ñ…Ñ¥½¸ ‰…¹‘É½¥‘à¹½É”é½É”µ­ÑàèÄ¸ÄÔ¸Àˆ¤(€€€¥µÁ±•µ•¹Ñ…Ñ¥½¸ ‰…¹‘É½¥‘à¹…Ñ¥Ù¥Ñäé…Ñ¥Ù¥Ñäµ½µÁ½Í”èÄ¸ä¸Ìˆ¤(€€€¥µÁ±•µ•¹Ñ…Ñ¥½¸ ‰…¹‘É½¥‘à¹±¥™•å±”é±¥™•å±”µÉÕ¹Ñ¥µ”µ­ÑàèÈ¸à¸Üˆ¤(€€€¥µÁ±•µ•¹Ñ…Ñ¥½¸ ‰…¹‘É½¥‘à¹±¥™•å±”é±¥™•å±”µÉÕ¹Ñ¥µ”µ½µÁ½Í”èÈ¸à¸Üˆ¤(€€€¥µÁ±•µ•¹Ñ…Ñ¥½¸ ‰…¹‘É½¥‘à¹±¥™•å±”é±¥™•å±”µÙ¥•Ýµ½‘•°µ½µÁ½Í”èÈ¸à¸Üˆ¤((€€€¥µÁ±•µ•¹Ñ…Ñ¥½¸¡Á±…Ñ™½É´ ‰…¹‘É½¥‘à¹½µÁ½Í”é½µÁ½Í”µ‰½´èÈÀÈÐ¸ÄÈ¸ÀÄˆ¤¤(€€€¥µÁ±•µ•¹Ñ…Ñ¥½¸ ‰…¹‘É½¥‘à¹½µÁ½Í”¹Õ¤éÕ¤ˆ¤(€€€¥µÁ±•µ•¹Ñ…Ñ¥½¸ ‰…¹‘É½¥‘à¹½µÁ½Í”¹Õ¤éÕ¤µÑ½½±¥¹œµÁÉ•Ù¥•Üˆ¤(€€€¥µÁ±•µ•¹Ñ…Ñ¥½¸ ‰…¹‘É½¥‘à¹½µÁ½Í”¹µ…Ñ•É¥…°Ìéµ…Ñ•É¥…°Ìˆ¤(€€€¥µÁ±•µ•¹Ñ…Ñ¥½¸ ‰…¹‘É½¥‘à¹½µÁ½Í”¹µ…Ñ•É¥…°éµ…Ñ•É¥…°µ¥½¹Ìµ•áÑ•¹‘•ˆ¤((€€€¥µÁ±•µ•¹Ñ…Ñ¥½¸ ‰…¹‘É½¥‘à¹Í•ÕÉ¥ÑäéÍ•ÕÉ¥ÑäµÉåÁÑ¼èÄ¸Ä¸Àµ…±Á¡„ÀØˆ¤(€€€¥µÁ±•µ•¹Ñ…Ñ¥½¸ ‰…¹‘É½¥‘à¹‘…Ñ…ÍÑ½É”é‘…Ñ…ÍÑ½É”µÁÉ•™•É•¹•ÌèÄ¸Ä¸Äˆ¤((€€€¥µÁ±•µ•¹Ñ…Ñ¥½¸ ‰½´¹ÍÅÕ…É•ÕÀ¹½­¡ÑÑÀÌé½­¡ÑÑÀèÐ¸ÄÈ¸Àˆ¤(€€€¥µÁ±•µ•¹Ñ…Ñ¥½¸ ‰½Éœ¹©•Ñ‰É…¥¹Ì¹­½Ñ±¥¹àé­½Ñ±¥¹àµÍ•É¥…±¥é…Ñ¥½¸µ©Í½¸èÄ¸Ü¸Ìˆ¤(€€€¥µÁ±•µ•¹Ñ…Ñ¥½¸ ‰½Éœ¹©•Ñ‰É…¥¹Ì¹­½Ñ±¥¹àé­½Ñ±¥¹àµ½É½ÕÑ¥¹•Ìµ…¹‘É½¥èÄ¸ä¸Àˆ¤((€€€€¼¼aÉ…ä½É”€¡½µ½‰¥±”¤¸	Õ¥±Ý¥Ñ ¹…Ñ¥Ù”½‰Õ¥±µ¹…Ñ¥Ù”¹Í …¹‘É½ÀÑ¡”H¡•É”¸(€€€¥µÁ±•µ•¹Ñ…Ñ¥½¸¡™¥±•QÉ•”¡µ…Á=˜ ‰‘¥ÈˆÑ¼€‰±¥‰Ìˆ°€‰¥¹±Õ‘”ˆÑ¼±¥ÍÑ=˜ ˆ¨¹……Èˆ°€ˆ¨¹©…Èˆ¤¤¤¤((€€€‘•‰Õ%µÁ±•µ•¹Ñ…Ñ¥½¸ ‰…¹‘É½¥‘à¹½µÁ½Í”¹Õ¤éÕ¤µÑ½½±¥¹œˆ¤)ô(