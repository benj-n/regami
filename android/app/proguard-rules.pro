# Keep default; no special rules for simple WebView wrapper.# Keep WebView clients

# If using JS interfaces, consider keeping annotated classes.-keep class com.regami.app.** { *; }

-dontnote android.webkit.**
-dontwarn android.webkit.**
