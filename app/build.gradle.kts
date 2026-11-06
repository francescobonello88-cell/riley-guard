plugins { id("com.android.application") }

android {
    namespace = "mt.riley.app"
    compileSdk = 34
    defaultConfig {
        applicationId = "mt.riley.app"
        minSdk = 24
        targetSdk = 34
        versionCode = 16
        versionName = "2.7"
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}
