package com.regami

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import android.util.Log
import androidx.core.app.NotificationCompat
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import java.net.HttpURLConnection
import java.net.URL

/**
 * Firebase Cloud Messaging service for receiving push notifications.
 *
 * Handles:
 * - New match notifications
 * - Match status changes (accepted, confirmed, rejected)
 * - New message notifications
 * - Token registration with backend
 */
class MyFirebaseMessagingService : FirebaseMessagingService() {

    companion object {
        private const val TAG = "FCMService"
        private const val CHANNEL_ID = "regami_notifications"
        private const val CHANNEL_NAME = "Regami Notifications"
        private const val NOTIFICATION_ID = 1

        // Notification types
        private const val TYPE_NEW_MATCH = "new_match"
        private const val TYPE_MATCH_ACCEPTED = "match_accepted"
        private const val TYPE_MATCH_CONFIRMED = "match_confirmed"
        private const val TYPE_MATCH_REJECTED = "match_rejected"
        private const val TYPE_NEW_MESSAGE = "new_message"
        private const val TYPE_GENERAL = "general"
    }

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
    }

    /**
     * Called when a new FCM token is generated.
     * Send the token to the backend for storage.
     */
    override fun onNewToken(token: String) {
        super.onNewToken(token)
        Log.d(TAG, "New FCM token: $token")

        // Save token locally
        saveTokenLocally(token)

        // Send token to backend
        sendTokenToBackend(token)
    }

    /**
     * Called when a push notification is received while app is in foreground.
     */
    override fun onMessageReceived(message: RemoteMessage) {
        super.onMessageReceived(message)

        Log.d(TAG, "Message received from: ${message.from}")
        Log.d(TAG, "Message data: ${message.data}")
        Log.d(TAG, "Message notification: ${message.notification}")

        // Handle data payload
        val data = message.data
        val type = data["type"] ?: TYPE_GENERAL
        val title = data["title"] ?: message.notification?.title ?: "Regami"
        val body = data["body"] ?: message.notification?.body ?: "Nouvelle notification"
        val deepLink = data["deep_link"]

        // Display notification
        showNotification(title, body, type, deepLink)
    }

    /**
     * Create notification channel for Android 8.0+ (API level 26+)
     */
    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val importance = NotificationManager.IMPORTANCE_HIGH
            val channel = NotificationChannel(CHANNEL_ID, CHANNEL_NAME, importance).apply {
                description = "Notifications pour les matchs et messages"
                enableVibration(true)
                enableLights(true)
            }

            val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            notificationManager.createNotificationChannel(channel)
        }
    }

    /**
     * Display a notification to the user
     */
    private fun showNotification(title: String, body: String, type: String, deepLink: String?) {
        val intent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            // Add deep link data if provided
            deepLink?.let { putExtra("deep_link", it) }
            putExtra("notification_type", type)
        }

        val pendingIntent = PendingIntent.getActivity(
            this,
            0,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        // Choose notification icon based on type
        val icon = when (type) {
            TYPE_NEW_MATCH -> android.R.drawable.ic_dialog_info
            TYPE_MATCH_ACCEPTED -> android.R.drawable.checkbox_on_background
            TYPE_MATCH_CONFIRMED -> android.R.drawable.checkbox_on_background
            TYPE_NEW_MESSAGE -> android.R.drawable.ic_dialog_email
            else -> android.R.drawable.ic_dialog_info
        }

        val notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(icon)
            .setContentTitle(title)
            .setContentText(body)
            .setAutoCancel(true)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setContentIntent(pendingIntent)
            .setStyle(NotificationCompat.BigTextStyle().bigText(body))
            .build()

        val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        notificationManager.notify(NOTIFICATION_ID, notification)
    }

    /**
     * Save FCM token to local preferences
     */
    private fun saveTokenLocally(token: String) {
        val prefs = getSharedPreferences("regami_prefs", Context.MODE_PRIVATE)
        prefs.edit().putString("fcm_token", token).apply()
        Log.d(TAG, "Token saved locally")
    }

    /**
     * Send FCM token to backend server
     */
    private fun sendTokenToBackend(token: String) {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val prefs = getSharedPreferences("regami_prefs", Context.MODE_PRIVATE)
                val authToken = prefs.getString("auth_token", null)

                if (authToken == null) {
                    Log.w(TAG, "No auth token found, will retry after login")
                    return@launch
                }

                val baseUrl = BuildConfig.WEB_APP_URL.ifEmpty { "http://10.0.2.2:8000" }
                    .replace("5173", "8000") // Replace frontend port with backend port
                val url = URL("$baseUrl/users/me/fcm-token")

                val connection = url.openConnection() as HttpURLConnection
                connection.apply {
                    requestMethod = "POST"
                    setRequestProperty("Content-Type", "application/json")
                    setRequestProperty("Authorization", "Bearer $authToken")
                    doOutput = true
                }

                val jsonBody = """{"fcm_token": "$token"}"""
                connection.outputStream.use { it.write(jsonBody.toByteArray()) }

                val responseCode = connection.responseCode
                if (responseCode == HttpURLConnection.HTTP_OK || responseCode == HttpURLConnection.HTTP_NO_CONTENT) {
                    Log.d(TAG, "Token successfully sent to backend")
                } else {
                    Log.e(TAG, "Failed to send token to backend: $responseCode")
                }

                connection.disconnect()
            } catch (e: Exception) {
                Log.e(TAG, "Error sending token to backend", e)
            }
        }
    }

    /**
     * Get the current FCM token
     */
    fun getCurrentToken(context: Context): String? {
        val prefs = context.getSharedPreferences("regami_prefs", Context.MODE_PRIVATE)
        return prefs.getString("fcm_token", null)
    }
}
