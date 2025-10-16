# Android Release Signing Guide

## Generating Release Keystore

### Create a new keystore

```bash
keytool -genkey -v -keystore regami-release-key.jks \
  -alias regami \
  -keyalg RSA \
  -keysize 2048 \
  -validity 10000

# Answer the prompts:
# Enter keystore password: [STORE_PASSWORD]
# Re-enter password: [STORE_PASSWORD]
# Enter key password for <regami>: [KEY_PASSWORD]
# What is your first and last name?: Regami Inc
# What is the name of your organizational unit?: Development
# What is the name of your organization?: Regami
# What is the name of your City or Locality?: Paris
# What is the name of your State or Province?: Ile-de-France
# What is the two-letter country code for this unit?: FR
```

### Store keystore securely

1. **Backup the keystore file** to a secure location (encrypted storage, password manager, etc.)
2. **Never commit keystore to Git** - add to `.gitignore`:
   ```
   *.jks
   *.keystore
   keystore.properties
   ```

3. **Create `keystore.properties` file** (local development):
   ```properties
   RELEASE_STORE_FILE=../regami-release-key.jks
   RELEASE_STORE_PASSWORD=your_store_password
   RELEASE_KEY_ALIAS=regami
   RELEASE_KEY_PASSWORD=your_key_password
   ```

## CI/CD Configuration

### GitHub Actions Secrets

Add these secrets to your GitHub repository:
- `ANDROID_KEYSTORE_BASE64`: Base64-encoded keystore file
- `ANDROID_KEYSTORE_PASSWORD`: Keystore password
- `ANDROID_KEY_ALIAS`: Key alias (regami)
- `ANDROID_KEY_PASSWORD`: Key password

### Encode keystore for CI

```bash
# Encode keystore to base64
base64 -i regami-release-key.jks | pbcopy  # macOS
base64 -i regami-release-key.jks           # Linux

# Paste the output into ANDROID_KEYSTORE_BASE64 secret
```

### Decode keystore in CI

```yaml
# .github/workflows/android-release.yml
- name: Decode keystore
  run: |
    echo "${{ secrets.ANDROID_KEYSTORE_BASE64 }}" | base64 -d > android/app/regami-release-key.jks
```

## Building Release APK/AAB

### Local build (requires keystore.properties)

```bash
cd android
./gradlew assembleRelease

# Output: app/build/outputs/apk/release/app-release.apk
```

### Build AAB for Play Store

```bash
cd android
./gradlew bundleRelease

# Output: app/build/outputs/bundle/release/app-release.aab
```

### Sign APK manually (if needed)

```bash
jarsigner -verbose -sigalg SHA256withRSA -digestalg SHA-256 \
  -keystore regami-release-key.jks \
  app/build/outputs/apk/release/app-release-unsigned.apk \
  regami

# Verify signing
jarsigner -verify -verbose -certs app/build/outputs/apk/release/app-release.apk
```

## Play Console Upload

### First time setup

1. **Create App** in Google Play Console
2. **App Access** - Declare restricted permissions usage
3. **Content Rating** - Complete questionnaire
4. **Privacy Policy** - Add URL (https://regami.com/privacy)
5. **Data Safety** - Declare data collection practices

### Release track workflow

1. **Internal Testing** (for team testing)
   - Upload AAB
   - Add internal testers
   - Get feedback

2. **Closed Testing** (alpha/beta)
   - Upload AAB
   - Add beta testers via email list or Google Group
   - Monitor crash reports

3. **Open Testing** (public beta)
   - Upload AAB
   - Make available to all users who opt-in

4. **Production**
   - Upload AAB
   - Staged rollout: 20% → 50% → 100%
   - Monitor metrics

### Version management

Update version in `android/app/build.gradle`:
```groovy
versionCode 2      // Increment for each release
versionName '1.1'  // User-visible version
```

## Security Best Practices

1. **Never commit keystore files**
2. **Use different keys for debug and release**
3. **Backup keystore in multiple secure locations**
4. **Rotate secrets if compromised**
5. **Use Play App Signing** (recommended) - Google manages your signing key
6. **Enable ProGuard/R8** for code obfuscation
7. **Test signing on CI before production**

## Troubleshooting

### "Key was created with errors"
- Ensure keystore password matches key password, or specify separately

### "Upload failed: Version code X has already been used"
- Increment `versionCode` in build.gradle

### "Signature verification failed"
- Ensure using correct keystore and passwords
- Check that keystore file is not corrupted

### App not installing from APK
- Ensure "Install from unknown sources" is enabled
- Check if debug version is already installed (uninstall first)

## Play App Signing (Recommended)

Let Google manage your app signing key:

1. **Initial upload**: Create upload key (separate from app signing key)
2. **Google stores**: The app signing key securely
3. **You upload**: APK/AAB signed with upload key
4. **Google re-signs**: With the app signing key before distribution

**Benefits:**
- Lost upload key can be reset
- Google optimizes APK for different devices
- Supports advanced features like app bundles

## Resources

- [Android App Signing](https://developer.android.com/studio/publish/app-signing)
- [Play Console Help](https://support.google.com/googleplay/android-developer)
- [Keystore Management](https://developer.android.com/studio/publish/app-signing#secure-key)
