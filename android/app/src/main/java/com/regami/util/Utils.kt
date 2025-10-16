package com.regami.util

import android.net.Uri
import android.util.Log
import org.json.JSONException
import org.json.JSONObject

/**
 * Utility functions for URI handling and validation
 */
object UriUtils {
    private const val TAG = "UriUtils"

    /**
     * Check if a URI is valid
     *
     * @param uri The URI to validate
     * @return True if the URI is valid and not null
     */
    fun isValidUri(uri: Uri?): Boolean {
        return uri != null && !uri.toString().isBlank()
    }

    /**
     * Check if a URI points to a local file
     *
     * @param uri The URI to check
     * @return True if the URI has file:// or content:// scheme
     */
    fun isLocalUri(uri: Uri): Boolean {
        val scheme = uri.scheme?.lowercase()
        return scheme == "file" || scheme == "content"
    }

    /**
     * Extract file extension from URI
     *
     * @param uri The URI to extract extension from
     * @return File extension (without dot) or empty string if none found
     */
    fun getFileExtension(uri: Uri): String {
        val path = uri.path ?: return ""
        val lastDot = path.lastIndexOf('.')
        return if (lastDot > 0 && lastDot < path.length - 1) {
            path.substring(lastDot + 1).lowercase()
        } else {
            ""
        }
    }

    /**
     * Check if URI points to an image file
     *
     * @param uri The URI to check
     * @return True if the URI has an image extension
     */
    fun isImageUri(uri: Uri): Boolean {
        val extension = getFileExtension(uri)
        return extension in setOf("jpg", "jpeg", "png", "gif", "webp", "bmp")
    }

    /**
     * Sanitize a URI string for logging (remove sensitive data)
     *
     * @param uri The URI to sanitize
     * @return Sanitized URI string safe for logging
     */
    fun sanitizeForLogging(uri: Uri): String {
        return uri.buildUpon()
            .clearQuery()
            .fragment(null)
            .build()
            .toString()
    }
}

/**
 * Utility functions for notification data parsing
 */
object NotificationUtils {
    private const val TAG = "NotificationUtils"

    /**
     * Parse notification data from FCM payload
     *
     * @param data Map of notification data
     * @return Parsed NotificationData or null if invalid
     */
    fun parseNotificationData(data: Map<String, String>): NotificationData? {
        return try {
            val type = data["type"] ?: return null
            val title = data["title"] ?: "Notification"
            val body = data["body"] ?: ""
            val deepLink = data["deepLink"]
            val extraData = data["data"]?.let { parseJson(it) }

            NotificationData(
                type = type,
                title = title,
                body = body,
                deepLink = deepLink,
                data = extraData
            )
        } catch (e: Exception) {
            Log.e(TAG, "Error parsing notification data", e)
            null
        }
    }

    /**
     * Parse JSON string to JSONObject
     *
     * @param jsonString The JSON string to parse
     * @return JSONObject or null if parsing fails
     */
    private fun parseJson(jsonString: String): JSONObject? {
        return try {
            JSONObject(jsonString)
        } catch (e: JSONException) {
            Log.w(TAG, "Failed to parse JSON: $jsonString", e)
            null
        }
    }

    /**
     * Extract deep link target from notification data
     *
     * @param data Notification data
     * @return Deep link URL or null
     */
    fun extractDeepLink(data: NotificationData): String? {
        // Try explicit deep link first
        data.deepLink?.let { return it }

        // Try to construct deep link from notification type
        return when (data.type) {
            "new_match" -> data.data?.optInt("match_id")?.let { "/matches/$it" }
            "new_message" -> data.data?.optInt("conversation_id")?.let { "/messages/$it" }
            "match_confirmed" -> data.data?.optInt("match_id")?.let { "/matches/$it" }
            else -> null
        }
    }
}

/**
 * Data class for parsed notification data
 */
data class NotificationData(
    val type: String,
    val title: String,
    val body: String,
    val deepLink: String? = null,
    val data: JSONObject? = null
)

/**
 * Utility functions for token handling
 */
object TokenUtils {
    private const val TAG = "TokenUtils"

    /**
     * Validate JWT token format (basic check)
     *
     * @param token The token to validate
     * @return True if the token has valid JWT structure
     */
    fun isValidJwtFormat(token: String): Boolean {
        val parts = token.split(".")
        return parts.size == 3 && parts.all { it.isNotBlank() }
    }

    /**
     * Extract user ID from JWT token (without verification)
     * This is for display purposes only - always verify tokens on the backend
     *
     * @param token The JWT token
     * @return User ID or null if extraction fails
     */
    fun extractUserIdFromJwt(token: String): String? {
        return try {
            val parts = token.split(".")
            if (parts.size != 3) return null

            val payload = parts[1]
            val decodedBytes = android.util.Base64.decode(
                payload,
                android.util.Base64.URL_SAFE or android.util.Base64.NO_WRAP
            )
            val decodedString = String(decodedBytes)
            val json = JSONObject(decodedString)

            json.optString("user_id").takeIf { it.isNotBlank() }
        } catch (e: Exception) {
            Log.w(TAG, "Failed to extract user ID from token", e)
            null
        }
    }

    /**
     * Sanitize token for logging (show only first/last few characters)
     *
     * @param token The token to sanitize
     * @return Sanitized token string
     */
    fun sanitizeForLogging(token: String): String {
        if (token.length <= 10) return "***"
        return "${token.take(5)}...${token.takeLast(5)}"
    }
}
