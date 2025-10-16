# Android WebView App

Minimal Android app that wraps the Regami web app in a WebView.

What it does:
- Launches a WebView pointing to a configurable URL.
- Enables JavaScript and DOM storage.

Configure target URL:
- By default in debug builds, the app opens http://10.0.2.2:5173 (Vite dev server on the host when using Android Emulator).
- You can override via a BuildConfig value in `app/build.gradle`:
	- debug build: `buildConfigField 'String', 'WEB_APP_URL', '"http://10.0.2.2:5173"'`
	- release build: set a non-empty value using `--project-prop WEB_APP_URL=https://app.example.com` or by editing the Gradle file.

Build and run (from project root):
- Open the `android/` folder in Android Studio Flamingo+.
- Select an emulator or device and click Run.
- Or via command line:
	- ./gradlew :app:assembleDebug
	- adb install -r app/build/outputs/apk/debug/app-debug.apk

Notes:
- INTERNET permission is declared for network access.
- For non-HTTPS dev URLs, cleartext traffic is enabled.
- If your API requires cookies or OAuth redirects, additional configuration may be needed.
