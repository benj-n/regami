# SSL Certificate Pinning for Regami Android

## Overview

SSL certificate pinning is a security technique that validates server certificates against known, trusted certificates to prevent man-in-the-middle (MITM) attacks. This document explains how SSL pinning is implemented in the Regami Android app.

## What is SSL Pinning?

SSL pinning enhances HTTPS security by:

1. **Preventing MITM Attacks** - Even if an attacker installs a rogue CA certificate on the device, pinned connections will fail
2. **Protecting Against Compromised CAs** - If a Certificate Authority is compromised, your app won't trust certificates from that CA
3. **Ensuring Server Identity** - Guarantees you're connecting to your actual server, not an imposter

## Implementation

### NetworkSecurity.kt

The `NetworkSecurity` object configures OkHttp with certificate pinning:

```kotlin
object NetworkSecurity {
    private const val PRODUCTION_DOMAIN = "api.regami.com"
    private const val STAGING_DOMAIN = "staging-api.regami.com"

    fun buildSecureClient(
        enablePinning: Boolean = true,
        useStaging: Boolean = false
    ): OkHttpClient {
        val builder = OkHttpClient.Builder()
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)

        if (enablePinning) {
            val domain = getPinnedDomain(useStaging)
            val certificatePinner = CertificatePinner.Builder()
                .add(domain, "sha256/PRIMARY_PIN_HERE")
                .add(domain, "sha256/BACKUP_PIN_HERE")
                .add(domain, "sha256/ROOT_CA_PIN_HERE")
                .build()

            builder.certificatePinner(certificatePinner)
        }

        return builder.build()
    }
}
```

### SecureWebViewClient.kt

The `SecureWebViewClient` intercepts WebView requests and routes API calls through the pinned OkHttpClient:

```kotlin
class SecureWebViewClient(
    private val okHttpClient: OkHttpClient,
    // ...
) : WebViewClient() {

    override fun shouldInterceptRequest(
        view: WebView?,
        request: WebResourceRequest?
    ): WebResourceResponse? {
        val url = request?.url?.toString() ?: return null

        if (shouldIntercept(url)) {
            return interceptWithOkHttp(request)
        }

        return super.shouldInterceptRequest(view, request)
    }
}
```

### MainActivity Integration

```kotlin
val okHttpClient = NetworkSecurity.buildSecureClient(
    enablePinning = NetworkSecurity.shouldEnablePinning(BuildConfig.DEBUG)
)

webView.webViewClient = SecureWebViewClient(
    okHttpClient = okHttpClient,
    onPageStarted = { url -> /* ... */ },
    onPageFinished = { url -> /* ... */ },
    onError = { url, code, description -> /* ... */ }
)
```

## Certificate Pin Generation

### Method 1: Using OpenSSL (Recommended)

```bash
# Get certificate from server
openssl s_client -servername api.regami.com -connect api.regami.com:443 < /dev/null | openssl x509 -outform DER > cert.der

# Generate SHA-256 pin
openssl x509 -in cert.der -inform DER -pubkey -noout | openssl pkey -pubin -outform DER | openssl dgst -sha256 -binary | openssl enc -base64

# Output: base64-encoded SHA-256 hash
# Example: AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=
```

### Method 2: Using OkHttp CertificatePinner

Add temporary logging to get pins:

```kotlin
val client = OkHttpClient.Builder()
    .certificatePinner(
        CertificatePinner.Builder()
            .add("api.regami.com", "sha256/TEMP_INVALID_PIN")
            .build()
    )
    .build()

// Make a request - it will fail and log the correct pins
val request = Request.Builder()
    .url("https://api.regami.com")
    .build()

try {
    client.newCall(request).execute()
} catch (e: SSLPeerUnverifiedException) {
    Log.e("SSL", "Certificate pins:", e)
    // Look for: "sha256/ACTUALPIN123=" in the exception message
}
```

### Method 3: Using curl

```bash
# Get certificate chain
curl -v https://api.regami.com 2>&1 | grep -A 20 "Server certificate"

# Extract and pin each certificate in the chain
```

## Pin Configuration Strategy

### Multiple Pins for Rotation

Always configure **at least 2 pins** to allow certificate rotation without app updates:

```kotlin
val certificatePinner = CertificatePinner.Builder()
    .add(domain, "sha256/PRIMARY_PIN")    // Current certificate
    .add(domain, "sha256/BACKUP_PIN")     // Backup certificate
    .add(domain, "sha256/ROOT_CA_PIN")    // Root CA certificate
    .build()
```

### Pin Types

1. **Leaf Certificate Pin** - The actual server certificate (rotates every 1-2 years)
2. **Intermediate CA Pin** - The intermediate certificate authority
3. **Root CA Pin** - The root certificate authority (rarely changes)

**Recommendation:** Pin both the leaf certificate and the root CA. This allows certificate renewal without app updates while maintaining security.

## Environment Configuration

### Production

```kotlin
private const val PRODUCTION_DOMAIN = "api.regami.com"

// Production pins (example - update with actual pins)
.add(PRODUCTION_DOMAIN, "sha256/47DEQpj8HBSa+/TImW+5JCeuQeRkm5NMpJWZG3hSuFU=")
.add(PRODUCTION_DOMAIN, "sha256/YLh1dUR9y6Kja30RrAn7JKnbQG/uEtLMkBgFF2Fuihg=")
```

### Staging

```kotlin
private const val STAGING_DOMAIN = "staging-api.regami.com"

// Staging pins
.add(STAGING_DOMAIN, "sha256/STAGING_PIN_1")
.add(STAGING_DOMAIN, "sha256/STAGING_PIN_2")
```

### Debug Builds

SSL pinning is **automatically disabled** in debug builds to allow:
- Charles Proxy / mitmproxy debugging
- Development with localhost
- Testing with self-signed certificates

```kotlin
val okHttpClient = NetworkSecurity.buildSecureClient(
    enablePinning = NetworkSecurity.shouldEnablePinning(BuildConfig.DEBUG)
)

fun shouldEnablePinning(isDebug: Boolean): Boolean {
    return !isDebug  // Disable in debug, enable in release
}
```

## Deployment Process

### Before Production Deployment

1. **Generate Real Pins**

```bash
# Get current certificate pin
openssl s_client -servername api.regami.com -connect api.regami.com:443 < /dev/null | \
  openssl x509 -outform DER | \
  openssl x509 -inform DER -pubkey -noout | \
  openssl pkey -pubin -outform DER | \
  openssl dgst -sha256 -binary | \
  openssl enc -base64
```

2. **Update NetworkSecurity.kt**

Replace placeholder pins with actual values:

```kotlin
val certificatePinner = CertificatePinner.Builder()
    .add(domain, "sha256/ACTUAL_PRIMARY_PIN_FROM_STEP_1")
    .add(domain, "sha256/ACTUAL_BACKUP_PIN_FROM_STEP_1")
    .build()
```

3. **Test Certificate Pinning**

Build a release APK and test:

```bash
./gradlew assembleRelease
adb install app/build/outputs/apk/release/app-release.apk
```

Try to connect through a proxy - it should fail with SSL pinning error.

4. **Verify in Logs**

```bash
adb logcat | grep "CertificatePinner"
# Should see: "Certificate pinning success" or pinning failure logs
```

### Certificate Rotation

When certificates expire or need rotation:

1. **Plan Ahead** - Update pins 30+ days before certificate expiration
2. **Release New App Version** - With both old and new certificate pins
3. **Wait for Adoption** - Ensure most users have updated (check analytics)
4. **Update Server Certificate** - After sufficient app adoption
5. **Remove Old Pin** - In next app update (optional)

### Emergency Certificate Update

If you need to update certificates immediately but many users have old app versions:

1. **Temporary Server Setup**
   - Keep old certificate active
   - Add new certificate (dual certificate setup)
   - Both pins will work

2. **Release Emergency Update**
   - Push new app version with updated pins
   - Consider force update mechanism

3. **Monitor**
   - Watch error rates in Sentry
   - Check SSL-related crashes

## Testing

### Unit Tests

```kotlin
@Test
fun `should enable pinning in release builds`() {
    val shouldPin = NetworkSecurity.shouldEnablePinning(isDebug = false)
    assertTrue(shouldPin)
}

@Test
fun `should disable pinning in debug builds`() {
    val shouldPin = NetworkSecurity.shouldEnablePinning(isDebug = true)
    assertFalse(shouldPin)
}

@Test
fun `should build secure client with pinning`() {
    val client = NetworkSecurity.buildSecureClient(enablePinning = true)
    assertNotNull(client)
}
```

### Manual Testing

#### Test Pinning is Disabled in Debug

```bash
# Build and install debug APK
./gradlew installDebug

# Connect through Charles Proxy
# App should work normally (pinning disabled)
```

#### Test Pinning is Enabled in Release

```bash
# Build and install release APK
./gradlew installRelease

# Try to intercept with Charles Proxy
# App should fail to connect (pinning enabled)
```

#### Test with Invalid Pin

Temporarily use an invalid pin to verify pinning works:

```kotlin
.add(domain, "sha256/INVALID_PIN_FOR_TESTING")
```

Build and run - API requests should fail with `SSLPeerUnverifiedException`.

## Debugging

### Common Issues

#### Issue: "Certificate pinning failure"

**Cause:** Certificate pins don't match server certificate

**Solution:**
1. Regenerate pins from current server certificate
2. Update `NetworkSecurity.kt` with correct pins
3. Rebuild app

#### Issue: "javax.net.ssl.SSLPeerUnverifiedException"

**Cause:** Pinning validation failed

**Solution:**
1. Check if correct domain is pinned
2. Verify pins are in correct format (`sha256/base64hash`)
3. Ensure server certificate hasn't changed

#### Issue: API requests work in debug but fail in release

**Cause:** Pinning is enabled in release but pins are incorrect

**Solution:**
1. Verify pins match production server
2. Test with `enablePinning = false` temporarily
3. Check server certificate chain

### Logging

Enable verbose logging:

```kotlin
val client = OkHttpClient.Builder()
    .addInterceptor(HttpLoggingInterceptor().apply {
        level = HttpLoggingInterceptor.Level.HEADERS
    })
    .certificatePinner(/* ... */)
    .build()
```

View certificate pinning logs:

```bash
adb logcat | grep -E "(CertificatePinner|SSL|TLS)"
```

## Security Considerations

### Do

- Pin multiple certificates (leaf + root CA)
- Test thoroughly before production release
- Plan for certificate rotation
- Disable pinning in debug builds
- Monitor SSL errors in production (Sentry)
- Document pin update process

### Don't

- Don't pin only one certificate (no backup)
- Don't hardcode pins without rotation plan
- Don't enable pinning in debug builds
- Don't ignore SSL errors in production
- Don't update certificates without app update
- Don't use weak or placeholder pins in production

## Monitoring

### Sentry Integration

SSL pinning failures are automatically reported to Sentry:

```kotlin
try {
    client.newCall(request).execute()
} catch (e: SSLPeerUnverifiedException) {
    Sentry.captureException(e)
    throw e
}
```

### Metrics to Track

- SSL pinning success rate
- Certificate validation failures
- Time to rotate certificates
- App version adoption rate

## Resources

- [OkHttp Certificate Pinning](https://square.github.io/okhttp/features/https/#certificate-pinning)
- [OWASP Certificate Pinning](https://owasp.org/www-community/controls/Certificate_and_Public_Key_Pinning)
- [Android Network Security Config](https://developer.android.com/training/articles/security-config)
- [Let's Encrypt Certificate Chains](https://letsencrypt.org/certificates/)

## Checklist

Before production deployment:

- [ ] Generate real certificate pins from production server
- [ ] Update `NetworkSecurity.kt` with actual pins (remove placeholders)
- [ ] Include backup pins for certificate rotation
- [ ] Test release build with actual production API
- [ ] Verify pinning works (proxy should fail)
- [ ] Verify pinning is disabled in debug builds
- [ ] Document pin update process for team
- [ ] Set calendar reminder for certificate expiration
- [ ] Configure Sentry alerts for SSL errors
- [ ] Test certificate rotation process
