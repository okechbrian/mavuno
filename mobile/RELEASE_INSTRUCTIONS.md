# Mavuno Yield: Android Release Instructions

This document outlines the steps required to build and sign the Mavuno Yield Android apps for production.

## 1. App Signing (Keystore)

Each app requires a release keystore. For simplicity in this protocol, we use a shared organization keystore for all 3 apps.

### Generate Keystore
Run the following command in the `mobile/keystore` directory:

```bash
keytool -genkey -v -keystore mavuno-release.jks -keyalg RSA -keysize 2048 -validity 10000 -alias mavuno-key
```

**Passwords:** 
The `gradle.properties` file currently expects `mavuno-production-2026`. If you change this, update `gradle.properties`.

## 2. Firebase Integration

The apps are pre-configured with Firebase Crashlytics and Analytics. 

1. Create a Firebase project at [console.firebase.google.com](https://console.firebase.google.com).
2. Add three Android apps:
   - `com.mavuno.farmer`
   - `com.mavuno.agent`
   - `com.mavuno.buyer`
3. Download the `google-services.json` for each and replace the placeholders in:
   - `mobile/app/google-services.json`
   - `mobile/agent-app/google-services.json`
   - `mobile/buyer-app/google-services.json`

## 3. Building Release Bundles (AAB)

To build the release version of all apps, run:

```bash
./gradlew bundleRelease
```

The output artifacts will be located in:
- `mobile/app/build/outputs/bundle/release/app-release.aab`
- `mobile/agent-app/build/outputs/bundle/release/agent-app-release.aab`
- `mobile/buyer-app/build/outputs/bundle/release/buyer-app-release.aab`

## 4. ProGuard / R8

Code shrinking and obfuscation are enabled in the `release` build type. If you add new data models or reflection-based libraries, update `proguard-rules.pro`.

## 5. In-App Updates

The `InAppUpdateManager` in the `core` module handles update prompts. Ensure the apps are uploaded to the Play Store Internal Test Track to test this functionality.
