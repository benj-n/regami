package com.regami

import android.Manifest
import android.annotation.SuppressLint
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.MediaStore
import android.util.Log
import android.view.View
import android.view.ViewGroup
import android.webkit.CookieManager
import android.webkit.JavascriptInterface
import android.webkit.ValueCallback
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.activity.OnBackPressedCallback
import androidx.activity.result.ActivityResultLauncher
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.core.content.FileProvider
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout
import com.google.firebase.messaging.FirebaseMessaging
import com.regami.network.NetworkSecurity
import com.regami.network.SecureWebViewClient
import java.io.File
import java.io.IOException
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class MainActivity : AppCompatActivity() {
    private lateinit var webView: WebView
    private lateinit var swipeRefreshLayout: SwipeRefreshLayout
    private lateinit var errorLayout: LinearLayout
    private var fileUploadCallback: ValueCallback<Array<Uri>>? = null
    private lateinit var fileChooserLauncher: ActivityResultLauncher<Intent>
    private lateinit var notificationPermissionLauncher: ActivityResultLauncher<String>
    private lateinit var cameraPermissionLauncher: ActivityResultLauncher<String>
    private var cameraPhotoUri: Uri? = null

    companion object {
        private const val TAG = "MainActivity"
    }

    @SuppressLint("SetJavaScriptEnabled", "AddJavascriptInterface")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Handle deep links
        handleDeepLink(intent)

        // Register notification permission launcher (Android 13+)
        notificationPermissionLauncher = registerForActivityResult(
            ActivityResultContracts.RequestPermission()
        ) { isGranted ->
            if (isGranted) {
                Log.d(TAG, "Notification permission granted")
                initializeFCM()
            } else {
                Log.w(TAG, "Notification permission denied")
                Toast.makeText(this, "Notifications désactivées", Toast.LENGTH_SHORT).show()
            }
        }

        // Register camera permission launcher
        cameraPermissionLauncher = registerForActivityResult(
            ActivityResultContracts.RequestPermission()
        ) { isGranted ->
            if (isGranted) {
                Log.d(TAG, "Camera permission granted, launching camera")
                launchCamera()
            } else {
                Log.w(TAG, "Camera permission denied")
                Toast.makeText(this, "Permission caméra refusée", Toast.LENGTH_SHORT).show()
                fileUploadCallback?.onReceiveValue(null)
                fileUploadCallback = null
            }
        }

        // Register file chooser launcher
        fileChooserLauncher = registerForActivityResult(
            ActivityResultContracts.StartActivityForResult()
        ) { result ->
            val data = result.data
            val uris = if (data != null) {
                val clipData = data.clipData
                if (clipData != null) {
                    // Multiple files selected from gallery
                    Array(clipData.itemCount) { i ->
                        clipData.getItemAt(i).uri
                    }
                } else if (data.data != null) {
                    // Single file selected from gallery
                    arrayOf(data.data!!)
                } else {
                    // Photo was taken with camera
                    cameraPhotoUri?.let { arrayOf(it) }
                }
            } else {
                // Photo was taken with camera (no data returned)
                cameraPhotoUri?.let { arrayOf(it) }
            }
            fileUploadCallback?.onReceiveValue(uris)
            fileUploadCallback = null
            cameraPhotoUri = null
        }

        // Create container layout
        val container = LinearLayout(this)
        container.orientation = LinearLayout.VERTICAL
        container.layoutParams = ViewGroup.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.MATCH_PARENT
        )

        // Create SwipeRefreshLayout
        swipeRefreshLayout = SwipeRefreshLayout(this)
        swipeRefreshLayout.layoutParams = ViewGroup.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.MATCH_PARENT
        )

        // Create WebView
        webView = WebView(this)
        webView.layoutParams = ViewGroup.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.MATCH_PARENT
        )

        // Create error layout (hidden by default)
        errorLayout = createErrorLayout()
        errorLayout.visibility = View.GONE

        // Nest WebView inside SwipeRefreshLayout
        swipeRefreshLayout.addView(webView)
        container.addView(swipeRefreshLayout)
        container.addView(errorLayout)
        setContentView(container)

        // Configure WebView
        with(webView.settings) {
            javaScriptEnabled = true
            domStorageEnabled = true
            mixedContentMode = WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE
            allowFileAccess = true
        }

        // Set WebChromeClient with file upload support
        webView.webChromeClient = object : WebChromeClient() {
            override fun onShowFileChooser(
                webView: WebView?,
                filePathCallback: ValueCallback<Array<Uri>>?,
                fileChooserParams: FileChooserParams?
            ): Boolean {
                // Cancel previous callback if exists
                fileUploadCallback?.onReceiveValue(null)
                fileUploadCallback = filePathCallback

                // Create camera intent
                val cameraIntent = Intent(MediaStore.ACTION_IMAGE_CAPTURE)
                cameraPhotoUri = createImageFileUri()

                cameraPhotoUri?.let {
                    cameraIntent.putExtra(MediaStore.EXTRA_OUTPUT, it)
                }

                // Create gallery intent
                val galleryIntent = fileChooserParams?.createIntent() ?: Intent(Intent.ACTION_GET_CONTENT).apply {
                    type = "image/*"
                    addCategory(Intent.CATEGORY_OPENABLE)
                    putExtra(Intent.EXTRA_ALLOW_MULTIPLE, fileChooserParams?.mode == FileChooserParams.MODE_OPEN_MULTIPLE)
                }

                // Create chooser with both options
                val chooserIntent = Intent.createChooser(galleryIntent, "Choisir une photo")
                chooserIntent.putExtra(Intent.EXTRA_INITIAL_INTENTS, arrayOf(cameraIntent))

                try {
                    fileChooserLauncher.launch(chooserIntent)
                    return true
                } catch (e: Exception) {
                    Log.e(TAG, "Failed to launch file chooser", e)
                    fileUploadCallback = null
                    cameraPhotoUri = null
                    return false
                }
            }
        }

        CookieManager.getInstance().setAcceptCookie(true)

        // Add JavaScript interface for FCM token communication
        webView.addJavascriptInterface(object : Any() {
            @JavascriptInterface
            fun getFCMToken(): String {
                val prefs = getSharedPreferences("regami_prefs", MODE_PRIVATE)
                return prefs.getString("fcm_token", "") ?: ""
            }

            @JavascriptInterface
            fun setAuthToken(token: String) {
                val prefs = getSharedPreferences("regami_prefs", MODE_PRIVATE)
                prefs.edit().putString("auth_token", token).apply()
                Log.d(TAG, "Auth token saved, will register FCM token")
                // Re-register FCM token now that we have auth
                initializeFCM()
            }
        }, "RegamiAndroid")

        // Configure SwipeRefreshLayout
        swipeRefreshLayout.setOnRefreshListener {
            webView.reload()
        }

        // Set color scheme to match app theme (purple gradient)
        swipeRefreshLayout.setColorSchemeColors(
            0xFF9333EA.toInt(), // purple-600
            0xFFA855F7.toInt(), // purple-500
            0xFFC084FC.toInt()  // purple-400
        )

        // Configure WebViewClient with SSL pinning for API requests
        // SSL pinning is automatically disabled in debug builds
        val okHttpClient = NetworkSecurity.buildSecureClient(
            enablePinning = NetworkSecurity.shouldEnablePinning(BuildConfig.DEBUG)
        )

        webView.webViewClient = SecureWebViewClient(
            okHttpClient = okHttpClient,
            onPageStarted = { url ->
                Log.d(TAG, "Page started loading: $url")
            },
            onPageFinished = { url ->
                Log.d(TAG, "Page finished loading: $url")
                swipeRefreshLayout.isRefreshing = false
            },
            onError = { url, errorCode, description ->
                Log.e(TAG, "Page load error: $url - $description")
                swipeRefreshLayout.isRefreshing = false
                showErrorPage(description)
            }
        )

        // Configure back button behavior
        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                when {
                    // If error page is visible, try to reload or exit
                    errorLayout.visibility == View.VISIBLE -> {
                        // User pressed back on error page, exit app
                        isEnabled = false
                        onBackPressedDispatcher.onBackPressed()
                    }
                    // If WebView can go back in history, navigate back
                    webView.canGoBack() -> {
                        webView.goBack()
                    }
                    // Otherwise, exit app
                    else -> {
                        isEnabled = false
                        onBackPressedDispatcher.onBackPressed()
                    }
                }
            }
        })

        // Request notification permission and initialize FCM
        requestNotificationPermission()

        val baseUrl = BuildConfig.WEB_APP_URL.ifEmpty { "http://10.0.2.2:5173" }
        webView.loadUrl(baseUrl)

        // Handle deep links from notifications
        handleNotificationIntent(intent)
    }

    override fun onNewIntent(intent: Intent?) {
        super.onNewIntent(intent)
        intent?.let { handleNotificationIntent(it) }
    }

    private fun handleNotificationIntent(intent: Intent) {
        val deepLink = intent.getStringExtra("deep_link")
        val notificationType = intent.getStringExtra("notification_type")

        if (deepLink != null) {
            Log.d(TAG, "Deep link received: $deepLink")
            // Navigate to the deep link in WebView
            val baseUrl = BuildConfig.WEB_APP_URL.ifEmpty { "http://10.0.2.2:5173" }
            webView.loadUrl("$baseUrl$deepLink")
        } else if (notificationType != null) {
            Log.d(TAG, "Notification type received: $notificationType")
            // Could navigate to specific pages based on type
            when (notificationType) {
                "new_match", "match_accepted", "match_confirmed" -> {
                    // Navigate to matches/notifications page
                }
                "new_message" -> {
                    // Navigate to messages page
                    val baseUrl = BuildConfig.WEB_APP_URL.ifEmpty { "http://10.0.2.2:5173" }
                    webView.loadUrl("$baseUrl/messages")
                }
            }
        }
    }

    private fun requestNotificationPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            when {
                ContextCompat.checkSelfPermission(
                    this,
                    Manifest.permission.POST_NOTIFICATIONS
                ) == PackageManager.PERMISSION_GRANTED -> {
                    Log.d(TAG, "Notification permission already granted")
                    initializeFCM()
                }
                else -> {
                    Log.d(TAG, "Requesting notification permission")
                    notificationPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
                }
            }
        } else {
            // No need to request permission on Android < 13
            initializeFCM()
        }
    }

    private fun initializeFCM() {
        FirebaseMessaging.getInstance().token.addOnCompleteListener { task ->
            if (!task.isSuccessful) {
                Log.w(TAG, "Fetching FCM registration token failed", task.exception)
                return@addOnCompleteListener
            }

            // Get new FCM registration token
            val token = task.result
            Log.d(TAG, "FCM token: $token")

            // Save token locally
            val prefs = getSharedPreferences("regami_prefs", MODE_PRIVATE)
            prefs.edit().putString("fcm_token", token).apply()

            // Send token to backend (will be handled by MyFirebaseMessagingService)
            // Note: This requires auth token to be set first via JavaScript interface
        }
    }

    private fun createErrorLayout(): LinearLayout {
        val layout = LinearLayout(this)
        layout.orientation = LinearLayout.VERTICAL
        layout.layoutParams = ViewGroup.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.MATCH_PARENT
        )
        layout.setPadding(48, 48, 48, 48)

        val errorText = TextView(this)
        errorText.text = "Impossible de charger la page\n\nVérifiez votre connexion Internet et réessayez."
        errorText.textSize = 18f
        errorText.textAlignment = View.TEXT_ALIGNMENT_CENTER
        val errorParams = LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.WRAP_CONTENT
        )
        errorParams.bottomMargin = 24
        errorText.layoutParams = errorParams

        val retryButton = Button(this)
        retryButton.text = "Réessayer"
        retryButton.layoutParams = LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.WRAP_CONTENT,
            ViewGroup.LayoutParams.WRAP_CONTENT
        )
        retryButton.setOnClickListener {
            hideErrorPage()
            webView.reload()
        }

        layout.addView(errorText)
        layout.addView(retryButton)

        return layout
    }

    private fun showErrorPage(error: WebResourceError?) {
        showErrorPage(error?.description?.toString() ?: "Unknown error")
    }

    private fun showErrorPage(errorDescription: String) {
        Log.e(TAG, "Showing error page: $errorDescription")
        swipeRefreshLayout.isRefreshing = false
        webView.visibility = View.GONE
        errorLayout.visibility = View.VISIBLE
    }

    private fun hideErrorPage() {
        errorLayout.visibility = View.GONE
        webView.visibility = View.VISIBLE
    }

    /**
     * Creates a URI for a new image file to store camera photos.
     * Uses FileProvider for secure file sharing on Android 7.0+.
     */
    private fun createImageFileUri(): Uri? {
        return try {
            // Create an image file name with timestamp
            val timeStamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.getDefault()).format(Date())
            val imageFileName = "REGAMI_${timeStamp}.jpg"

            // Get the app's cache directory
            val storageDir = File(cacheDir, "camera_photos")
            if (!storageDir.exists()) {
                storageDir.mkdirs()
            }

            val imageFile = File(storageDir, imageFileName)

            // Use FileProvider to get a content URI
            FileProvider.getUriForFile(
                this,
                "${applicationContext.packageName}.fileprovider",
                imageFile
            )
        } catch (e: IOException) {
            Log.e(TAG, "Error creating image file", e)
            null
        }
    }

    /**
     * Launches the camera to capture a photo.
     * Checks for camera permission first.
     */
    private fun launchCamera() {
        when {
            ContextCompat.checkSelfPermission(
                this,
                Manifest.permission.CAMERA
            ) == PackageManager.PERMISSION_GRANTED -> {
                // Permission already granted, launch camera
                val cameraIntent = Intent(MediaStore.ACTION_IMAGE_CAPTURE)
                cameraPhotoUri = createImageFileUri()

                cameraPhotoUri?.let {
                    cameraIntent.putExtra(MediaStore.EXTRA_OUTPUT, it)
                    try {
                        fileChooserLauncher.launch(cameraIntent)
                    } catch (e: Exception) {
                        Log.e(TAG, "Failed to launch camera", e)
                        fileUploadCallback?.onReceiveValue(null)
                        fileUploadCallback = null
                        cameraPhotoUri = null
                    }
                } ?: run {
                    Log.e(TAG, "Failed to create image file URI")
                    fileUploadCallback?.onReceiveValue(null)
                    fileUploadCallback = null
                }
            }
            else -> {
                // Request permission
                cameraPermissionLauncher.launch(Manifest.permission.CAMERA)
            }
        }
    }

    /**
     * Handle deep links from external sources
     */
    private fun handleDeepLink(intent: Intent?) {
        val data: Uri? = intent?.data
        if (data != null) {
            Log.d(TAG, "Deep link received: $data")
            val path = data.path
            // Deep link will be handled by the web app
            // The WebView will navigate to the correct page based on the URL
        }
    }

    override fun onNewIntent(intent: Intent?) {
        super.onNewIntent(intent)
        setIntent(intent)
        handleDeepLink(intent)
    }

    /**
     * JavaScript interface for native sharing
     */
    inner class ShareInterface {
        @JavascriptInterface
        fun shareDogProfile(dogName: String, dogId: String, profileUrl: String) {
            runOnUiThread {
                val shareIntent = Intent().apply {
                    action = Intent.ACTION_SEND
                    type = "text/plain"
                    putExtra(Intent.EXTRA_SUBJECT, "Découvrez $dogName sur Regami")
                    putExtra(
                        Intent.EXTRA_TEXT,
                        "Regardez le profil de $dogName sur Regami: $profileUrl"
                    )
                }
                startActivity(Intent.createChooser(shareIntent, "Partager via"))
            }
        }

        @JavascriptInterface
        fun shareOffer(offerTitle: String, offerUrl: String) {
            runOnUiThread {
                val shareIntent = Intent().apply {
                    action = Intent.ACTION_SEND
                    type = "text/plain"
                    putExtra(Intent.EXTRA_SUBJECT, "Offre de garde sur Regami")
                    putExtra(
                        Intent.EXTRA_TEXT,
                        "$offerTitle\n\nVoir sur Regami: $offerUrl"
                    )
                }
                startActivity(Intent.createChooser(shareIntent, "Partager via"))
            }
        }
    }
}
