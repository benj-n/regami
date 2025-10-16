# Android Testing Guide

## Overview

This guide covers testing strategies for the Regami Android application, including unit tests, instrumented tests, and continuous integration.

## Test Structure

```
android/app/src/
├── test/                           # Unit tests (JVM)
│   └── java/com/regami/
│       ├── network/
│       │   └── NetworkSecurityTest.kt
│       └── util/
│           └── UtilsTest.kt
└── androidTest/                    # Instrumented tests (Device/Emulator)
    └── java/com/regami/
        ├── MainActivityInstrumentedTest.kt
        ├── WebViewSecurityTest.kt
        └── FileUploadTest.kt
```

## Testing Technologies

- **JUnit 4.13.2** - Unit testing framework
- **Mockito 5.7.0** - Mocking framework
- **Robolectric 4.11.1** - Android unit testing without devices
- **Espresso 3.5.1** - Android instrumented testing
- **AndroidX Test** - Android testing utilities

## Unit Tests (JVM)

Unit tests run on the JVM and are fast. They test business logic without Android dependencies or with Robolectric for Android components.

### Running Unit Tests

```bash
# Run all unit tests
cd android
./gradlew test

# Run tests for specific variant
./gradlew testDebugUnitTest

# Run with coverage
./gradlew testDebugUnitTest jacocoTestReport

# Run specific test class
./gradlew test --tests "com.regami.network.NetworkSecurityTest"

# Run specific test method
./gradlew test --tests "com.regami.util.UriUtilsTest.should validate non-null URI"
```

### Unit Test Examples

#### Testing SSL Pinning Configuration

```kotlin
@Test
fun `should enable pinning in release builds`() {
    val shouldPin = NetworkSecurity.shouldEnablePinning(isDebug = false)
    assertTrue("Pinning should be enabled in release", shouldPin)
}
```

#### Testing Utility Functions with Robolectric

```kotlin
@RunWith(RobolectricTestRunner::class)
@Config(sdk = [28])
class UriUtilsTest {
    @Test
    fun `should detect file URI as local`() {
        val uri = Uri.parse("file:///storage/emulated/0/picture.jpg")
        assertTrue("file:// URI should be local", UriUtils.isLocalUri(uri))
    }
}
```

## Instrumented Tests (Device/Emulator)

Instrumented tests run on actual Android devices or emulators. They test UI interactions and Android-specific functionality.

### Running Instrumented Tests

```bash
# Ensure device/emulator is connected
adb devices

# Run all instrumented tests
cd android
./gradlew connectedAndroidTest

# Run tests for specific variant
./gradlew connectedDebugAndroidTest

# Run specific test class
./gradlew connectedAndroidTest -Pandroid.testInstrumentationRunnerArguments.class=com.regami.MainActivityTest

# Run with coverage
./gradlew createDebugCoverageReport
```

### Instrumented Test Examples

#### Testing Activity Launch

```kotlin
@RunWith(AndroidJUnit4::class)
@LargeTest
class MainActivityTest {
    @get:Rule
    val activityRule = ActivityScenarioRule(MainActivity::class.java)

    @Test
    fun testActivityLaunches() {
        activityRule.scenario.onActivity { activity ->
            assert(activity != null)
        }
    }
}
```

#### Testing WebView

```kotlin
@Test
fun testWebViewLoadsSuccessfully() {
    Thread.sleep(3000) // Wait for load

    activityRule.scenario.onActivity { activity ->
        val webView = activity.findViewById<WebView>(...)
        assert(webView.url != null)
    }
}
```

#### Testing Permissions

```kotlin
@get:Rule
val permissionRule: GrantPermissionRule = GrantPermissionRule.grant(
    Manifest.permission.POST_NOTIFICATIONS,
    Manifest.permission.CAMERA
)

@Test
fun testCameraPermissionGranted() {
    // Test camera functionality
}
```

## Test Coverage

### Coverage Requirements

- **Unit Tests:** >60% coverage for utility classes
- **Integration Tests:** All critical user flows
- **Instrumented Tests:** Key UI interactions

### Generating Coverage Reports

```bash
# Unit test coverage
./gradlew testDebugUnitTest jacocoTestReport

# Instrumented test coverage
./gradlew createDebugCoverageReport

# View reports
open app/build/reports/jacoco/testDebugUnitTest/html/index.html
open app/build/reports/coverage/androidTest/debug/index.html
```

## Testing Best Practices

### 1. Test Naming

Use descriptive test names that explain what is being tested:

```kotlin
@Test
fun `should validate correct JWT format`() { ... }

@Test
fun `should reject JWT with too few parts`() { ... }
```

### 2. Arrange-Act-Assert Pattern

```kotlin
@Test
fun `should parse valid notification data`() {
    // Arrange
    val data = mapOf("type" to "new_match", "title" to "New Match!")

    // Act
    val parsed = NotificationUtils.parseNotificationData(data)

    // Assert
    assertNotNull("Should parse notification data", parsed)
    assertEquals("Should extract type", "new_match", parsed?.type)
}
```

### 3. Test Isolation

Each test should be independent:

```kotlin
@Before
fun setUp() {
    // Clear shared state
    context.getSharedPreferences("regami_prefs", Context.MODE_PRIVATE)
        .edit().clear().apply()
}

@After
fun tearDown() {
    // Clean up resources
}
```

### 4. Use Test Doubles

Mock external dependencies:

```kotlin
@Test
fun `should handle network error`() {
    val mockClient = mock<OkHttpClient>()
    whenever(mockClient.newCall(any())).thenThrow(IOException("Network error"))

    // Test error handling
}
```

### 5. Test Both Success and Failure Cases

```kotlin
@Test
fun `should parse valid token`() { /* ... */ }

@Test
fun `should reject invalid token`() { /* ... */ }

@Test
fun `should handle null token`() { /* ... */ }
```

## Continuous Integration

Tests run automatically on GitHub Actions for every push and pull request.

### CI Test Stages

1. **Lint** (10 min) - Code quality checks
2. **Unit Tests** (15 min) - Fast JVM tests
3. **Build** (20 min) - Compile debug + release APKs
4. **Instrumented Tests** (30 min) - Emulator tests (main/develop only)
5. **Security Scan** (10 min) - Dependency analysis

### CI Configuration

See `.github/workflows/android-ci.yml` for full configuration.

```yaml
on:
  push:
    branches: [main, develop]
    paths: ['android/**']
  pull_request:
    branches: [main, develop]
    paths: ['android/**']
```

### Viewing CI Results

1. Go to GitHub Actions tab
2. Select "Android CI" workflow
3. Click on specific run to see results
4. Download test reports from artifacts

## Debugging Tests

### Running Tests with Debug Output

```bash
# Verbose output
./gradlew test --info

# Debug output
./gradlew test --debug

# Stack traces
./gradlew test --stacktrace
```

### Android Studio

1. Right-click test class/method
2. Select "Run 'TestName'" or "Debug 'TestName'"
3. View results in Run panel
4. Set breakpoints for debugging

### Emulator Logs

```bash
# View logcat during instrumented tests
adb logcat | grep "MainActivity"

# Filter by tag
adb logcat -s TAG_NAME

# Clear logs
adb logcat -c
```

## Common Test Scenarios

### Testing Network Security

```kotlin
@Test
fun `should enable SSL pinning in production`() {
    val client = NetworkSecurity.buildSecureClient(enablePinning = true)
    assertNotNull(client)
    // Verify certificate pinning is configured
}
```

### Testing Data Parsing

```kotlin
@Test
fun `should extract user ID from JWT`() {
    val token = "header.payload.signature"
    val userId = TokenUtils.extractUserIdFromJwt(token)
    assertEquals("123", userId)
}
```

### Testing UI Interactions

```kotlin
@Test
fun testSwipeToRefresh() {
    onView(withId(R.id.swipeRefreshLayout))
        .perform(swipeDown())

    // Verify refresh triggered
}
```

### Testing Deep Links

```kotlin
@Test
fun testDeepLinkNavigation() {
    val intent = Intent(context, MainActivity::class.java).apply {
        putExtra("deep_link", "/matches/123")
    }

    val scenario = ActivityScenario.launch<MainActivity>(intent)
    scenario.onActivity { activity ->
        assert(activity.webView.url?.contains("/matches/123") == true)
    }
}
```

## Test Data

### Test Users

For instrumented tests that require authentication:

```kotlin
val testOwner = mapOf(
    "email" to "test-owner@regami.com",
    "password" to "TestPassword123!"
)

val testSeeker = mapOf(
    "email" to "test-seeker@regami.com",
    "password" to "TestPassword123!"
)
```

### Mock Data

```kotlin
val mockFCMToken = "test_fcm_token_123"
val mockAuthToken = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
val mockDeepLink = "/matches/123"
```

## Troubleshooting

### Tests Failing on CI but Passing Locally

- Check Android API level differences
- Verify emulator configuration
- Check for race conditions (add appropriate waits)
- Review CI logs for specific errors

### Slow Instrumented Tests

- Use Robolectric for Android unit tests instead
- Run instrumented tests only on main/develop branches
- Cache AVD snapshots in CI
- Use `@LargeTest` annotation for slow tests

### Flaky Tests

- Add proper wait/synchronization
- Use Espresso idling resources
- Mock time-dependent code
- Avoid hardcoded delays (use `waitUntil`)

### Permission Issues

- Use `GrantPermissionRule` for automatic permission granting
- Check Android version compatibility (API 23+ requires runtime permissions)

## Resources

- [JUnit 4 Documentation](https://junit.org/junit4/)
- [Mockito Documentation](https://site.mockito.org/)
- [Robolectric Documentation](http://robolectric.org/)
- [Espresso Documentation](https://developer.android.com/training/testing/espresso)
- [Android Testing Codelab](https://developer.android.com/codelabs/advanced-android-kotlin-training-testing-basics)

## Next Steps

1. Add more unit tests for new utility classes
2. Expand instrumented tests for edge cases
3. Add UI testing with Espresso Test Recorder
4. Integrate screenshot testing with Shot
5. Add performance testing with Macrobenchmark
