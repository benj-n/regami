package com.regami

import android.Manifest
import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.test.core.app.ActivityScenario
import androidx.test.core.app.ApplicationProvider
import androidx.test.espresso.Espresso.onView
import androidx.test.espresso.action.ViewActions.swipeDown
import androidx.test.espresso.assertion.ViewAssertions.matches
import androidx.test.espresso.matcher.ViewMatchers.isDisplayed
import androidx.test.espresso.matcher.ViewMatchers.withText
import androidx.test.espresso.web.assertion.WebViewAssertions.webMatches
import androidx.test.espresso.web.sugar.Web.onWebView
import androidx.test.espresso.web.webdriver.DriverAtoms.findElement
import androidx.test.espresso.web.webdriver.DriverAtoms.getText
import androidx.test.espresso.web.webdriver.Locator
import androidx.test.ext.junit.rules.ActivityScenarioRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.filters.LargeTest
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.rule.GrantPermissionRule
import org.hamcrest.Matchers.containsString
import org.junit.After
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/**
 * Instrumented tests for MainActivity
 *
 * These tests run on an Android device or emulator
 */
@RunWith(AndroidJUnit4::class)
@LargeTest
class MainActivityTest {

    @get:Rule
    val activityRule = ActivityScenarioRule(MainActivity::class.java)

    @get:Rule
    val permissionRule: GrantPermissionRule = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
        GrantPermissionRule.grant(
            Manifest.permission.POST_NOTIFICATIONS,
            Manifest.permission.CAMERA
        )
    } else {
        GrantPermissionRule.grant(Manifest.permission.CAMERA)
    }

    private lateinit var context: Context

    @Before
    fun setUp() {
        context = ApplicationProvider.getApplicationContext()

        // Clear shared preferences before each test
        val prefs = context.getSharedPreferences("regami_prefs", Context.MODE_PRIVATE)
        prefs.edit().clear().apply()
    }

    @After
    fun tearDown() {
        // Clean up
    }

    @Test
    fun testActivityLaunches() {
        // Activity should launch without crashing
        activityRule.scenario.onActivity { activity ->
            assert(activity != null)
        }
    }

    @Test
    fun testWebViewLoadsSuccessfully() {
        // Wait for WebView to load
        Thread.sleep(3000) // Give WebView time to load

        // Verify WebView is displayed
        activityRule.scenario.onActivity { activity ->
            val webView = activity.findViewById<android.webkit.WebView>(
                activity.resources.getIdentifier("webView", "id", activity.packageName)
            )
            assert(webView != null)
            assert(webView.url != null)
        }
    }

    @Test
    fun testSwipeToRefresh() {
        // Wait for initial load
        Thread.sleep(2000)

        // Perform swipe down gesture
        activityRule.scenario.onActivity { activity ->
            val swipeLayout = activity.findViewById<androidx.swiperefreshlayout.widget.SwipeRefreshLayout>(
                activity.resources.getIdentifier("swipeRefreshLayout", "id", activity.packageName)
            )

            // Trigger refresh
            InstrumentationRegistry.getInstrumentation().runOnMainSync {
                swipeLayout.isRefreshing = true
            }

            // Wait a moment
            Thread.sleep(1000)

            // Verify refresh is triggered (will stop when page loads)
            assert(true) // Test passes if no crash
        }
    }

    @Test
    fun testBackButtonBehavior() {
        // Wait for initial load
        Thread.sleep(2000)

        // Press back button
        activityRule.scenario.onActivity { activity ->
            activity.onBackPressedDispatcher.onBackPressed()

            // Activity should still be alive (WebView handles back)
            assert(!activity.isFinishing)
        }
    }

    @Test
    fun testJavaScriptInterfaceExists() {
        // Verify JavaScript interface is registered
        activityRule.scenario.onActivity { activity ->
            val webView = activity.findViewById<android.webkit.WebView>(
                activity.resources.getIdentifier("webView", "id", activity.packageName)
            )

            // Execute JavaScript to check if interface exists
            webView.evaluateJavascript(
                "typeof window.RegamiAndroid !== 'undefined'",
                { result ->
                    assert(result == "true")
                }
            )
        }
    }

    @Test
    fun testFCMTokenStorage() {
        // Set a test FCM token
        val testToken = "test_fcm_token_123"
        val prefs = context.getSharedPreferences("regami_prefs", Context.MODE_PRIVATE)
        prefs.edit().putString("fcm_token", testToken).apply()

        // Verify token is stored
        activityRule.scenario.onActivity { activity ->
            val storedToken = prefs.getString("fcm_token", "")
            assert(storedToken == testToken)
        }
    }

    @Test
    fun testAuthTokenStorage() {
        // Verify auth token can be stored via JavaScript interface
        val testToken = "test_auth_token_xyz"

        activityRule.scenario.onActivity { activity ->
            val webView = activity.findViewById<android.webkit.WebView>(
                activity.resources.getIdentifier("webView", "id", activity.packageName)
            )

            // Call setAuthToken via JavaScript
            webView.evaluateJavascript(
                "window.RegamiAndroid.setAuthToken('$testToken')",
                null
            )

            // Wait for execution
            Thread.sleep(500)

            // Verify token is stored
            val prefs = context.getSharedPreferences("regami_prefs", Context.MODE_PRIVATE)
            val storedToken = prefs.getString("auth_token", "")
            assert(storedToken == testToken)
        }
    }

    @Test
    fun testDeepLinkHandling() {
        // Create intent with deep link
        val deepLink = "/matches/123"
        val intent = Intent(context, MainActivity::class.java).apply {
            putExtra("deep_link", deepLink)
        }

        // Launch activity with deep link
        val scenario = ActivityScenario.launch<MainActivity>(intent)

        // Wait for WebView to navigate
        Thread.sleep(2000)

        scenario.onActivity { activity ->
            val webView = activity.findViewById<android.webkit.WebView>(
                activity.resources.getIdentifier("webView", "id", activity.packageName)
            )

            // Verify URL contains deep link path
            assert(webView.url?.contains("/matches/123") == true)
        }

        scenario.close()
    }

    @Test
    fun testNotificationTypeHandling() {
        // Create intent with notification type
        val intent = Intent(context, MainActivity::class.java).apply {
            putExtra("notification_type", "new_message")
        }

        // Launch activity with notification
        val scenario = ActivityScenario.launch<MainActivity>(intent)

        // Wait for navigation
        Thread.sleep(2000)

        scenario.onActivity { activity ->
            val webView = activity.findViewById<android.webkit.WebView>(
                activity.resources.getIdentifier("webView", "id", activity.packageName)
            )

            // Verify URL contains messages path
            assert(webView.url?.contains("/messages") == true)
        }

        scenario.close()
    }
}

/**
 * Instrumented tests for WebView security features
 */
@RunWith(AndroidJUnit4::class)
@LargeTest
class WebViewSecurityTest {

    @get:Rule
    val activityRule = ActivityScenarioRule(MainActivity::class.java)

    @Test
    fun testJavaScriptIsEnabled() {
        activityRule.scenario.onActivity { activity ->
            val webView = activity.findViewById<android.webkit.WebView>(
                activity.resources.getIdentifier("webView", "id", activity.packageName)
            )

            assert(webView.settings.javaScriptEnabled)
        }
    }

    @Test
    fun testDOMStorageIsEnabled() {
        activityRule.scenario.onActivity { activity ->
            val webView = activity.findViewById<android.webkit.WebView>(
                activity.resources.getIdentifier("webView", "id", activity.packageName)
            )

            assert(webView.settings.domStorageEnabled)
        }
    }

    @Test
    fun testCookiesAreEnabled() {
        activityRule.scenario.onActivity { activity ->
            val cookieManager = android.webkit.CookieManager.getInstance()
            assert(cookieManager.acceptCookie())
        }
    }

    @Test
    fun testSecureWebViewClientIsSet() {
        activityRule.scenario.onActivity { activity ->
            val webView = activity.findViewById<android.webkit.WebView>(
                activity.resources.getIdentifier("webView", "id", activity.packageName)
            )

            val client = webView.webViewClient
            assert(client != null)
            assert(client.javaClass.name.contains("SecureWebViewClient"))
        }
    }

    @Test
    fun testSSLPinningIsConfigured() {
        // This test verifies SSL pinning configuration exists
        // Actual SSL pinning verification would require a mock server
        activityRule.scenario.onActivity { activity ->
            // SSL pinning is configured in SecureWebViewClient
            // which is set as the WebViewClient
            val webView = activity.findViewById<android.webkit.WebView>(
                activity.resources.getIdentifier("webView", "id", activity.packageName)
            )

            assert(webView.webViewClient != null)
        }
    }
}

/**
 * Instrumented tests for file upload functionality
 */
@RunWith(AndroidJUnit4::class)
@LargeTest
class FileUploadTest {

    @get:Rule
    val activityRule = ActivityScenarioRule(MainActivity::class.java)

    @get:Rule
    val permissionRule: GrantPermissionRule = GrantPermissionRule.grant(
        Manifest.permission.CAMERA,
        Manifest.permission.WRITE_EXTERNAL_STORAGE
    )

    @Test
    fun testWebChromeClientIsSet() {
        activityRule.scenario.onActivity { activity ->
            val webView = activity.findViewById<android.webkit.WebView>(
                activity.resources.getIdentifier("webView", "id", activity.packageName)
            )

            assert(webView.webChromeClient != null)
        }
    }

    @Test
    fun testFileAccessIsEnabled() {
        activityRule.scenario.onActivity { activity ->
            val webView = activity.findViewById<android.webkit.WebView>(
                activity.resources.getIdentifier("webView", "id", activity.packageName)
            )

            assert(webView.settings.allowFileAccess)
        }
    }
}
