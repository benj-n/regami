package com.regami.util

import android.net.Uri
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

/**
 * Unit tests for UriUtils
 * Uses Robolectric for Android Uri class
 */
@RunWith(RobolectricTestRunner::class)
@Config(sdk = [28])
class UriUtilsTest {

    @Test
    fun `should validate non-null URI`() {
        val uri = Uri.parse("https://example.com/path")
        assertTrue("Valid URI should be valid", UriUtils.isValidUri(uri))
    }

    @Test
    fun `should reject null URI`() {
        assertFalse("Null URI should be invalid", UriUtils.isValidUri(null))
    }

    @Test
    fun `should detect file URI as local`() {
        val uri = Uri.parse("file:///storage/emulated/0/picture.jpg")
        assertTrue("file:// URI should be local", UriUtils.isLocalUri(uri))
    }

    @Test
    fun `should detect content URI as local`() {
        val uri = Uri.parse("content://media/external/images/media/123")
        assertTrue("content:// URI should be local", UriUtils.isLocalUri(uri))
    }

    @Test
    fun `should detect HTTP URI as not local`() {
        val uri = Uri.parse("https://example.com/image.jpg")
        assertFalse("https:// URI should not be local", UriUtils.isLocalUri(uri))
    }

    @Test
    fun `should extract jpg extension`() {
        val uri = Uri.parse("file:///path/to/image.jpg")
        assertEquals("Should extract jpg extension", "jpg", UriUtils.getFileExtension(uri))
    }

    @Test
    fun `should extract png extension`() {
        val uri = Uri.parse("content://media/image.PNG")
        assertEquals("Should extract png extension (lowercase)", "png", UriUtils.getFileExtension(uri))
    }

    @Test
    fun `should return empty string for URI without extension`() {
        val uri = Uri.parse("file:///path/to/noextension")
        assertEquals("Should return empty string", "", UriUtils.getFileExtension(uri))
    }

    @Test
    fun `should detect image URI by extension`() {
        val extensions = listOf("jpg", "jpeg", "png", "gif", "webp", "bmp")
        extensions.forEach { ext ->
            val uri = Uri.parse("file:///image.$ext")
            assertTrue("$ext should be detected as image", UriUtils.isImageUri(uri))
        }
    }

    @Test
    fun `should reject non-image URI`() {
        val uri = Uri.parse("file:///document.pdf")
        assertFalse("PDF should not be detected as image", UriUtils.isImageUri(uri))
    }

    @Test
    fun `should sanitize URI for logging by removing query and fragment`() {
        val uri = Uri.parse("https://example.com/path?token=secret123#fragment")
        val sanitized = UriUtils.sanitizeForLogging(uri)

        assertFalse("Should remove query", sanitized.contains("token"))
        assertFalse("Should remove fragment", sanitized.contains("fragment"))
        assertTrue("Should keep path", sanitized.contains("/path"))
    }
}

/**
 * Unit tests for NotificationUtils
 */
@RunWith(RobolectricTestRunner::class)
@Config(sdk = [28])
class NotificationUtilsTest {

    @Test
    fun `should parse valid notification data`() {
        val data = mapOf(
            "type" to "new_match",
            "title" to "New Match!",
            "body" to "You have a new match",
            "deepLink" to "/matches/123"
        )

        val parsed = NotificationUtils.parseNotificationData(data)

        assertNotNull("Should parse notification data", parsed)
        assertEquals("Should extract type", "new_match", parsed?.type)
        assertEquals("Should extract title", "New Match!", parsed?.title)
        assertEquals("Should extract body", "You have a new match", parsed?.body)
        assertEquals("Should extract deep link", "/matches/123", parsed?.deepLink)
    }

    @Test
    fun `should use default title when missing`() {
        val data = mapOf(
            "type" to "new_message",
            "body" to "New message received"
        )

        val parsed = NotificationUtils.parseNotificationData(data)

        assertNotNull("Should parse notification data", parsed)
        assertEquals("Should use default title", "Notification", parsed?.title)
    }

    @Test
    fun `should return null for invalid notification data`() {
        val data = mapOf(
            "title" to "No Type",
            "body" to "Missing type field"
        )

        val parsed = NotificationUtils.parseNotificationData(data)

        assertNull("Should return null for missing type", parsed)
    }

    @Test
    fun `should extract deep link for new match`() {
        val data = NotificationData(
            type = "new_match",
            title = "New Match",
            body = "Match found",
            deepLink = null,
            data = org.json.JSONObject("""{"match_id": 456}""")
        )

        val deepLink = NotificationUtils.extractDeepLink(data)

        assertEquals("Should construct match deep link", "/matches/456", deepLink)
    }

    @Test
    fun `should extract deep link for new message`() {
        val data = NotificationData(
            type = "new_message",
            title = "New Message",
            body = "Message received",
            deepLink = null,
            data = org.json.JSONObject("""{"conversation_id": 789}""")
        )

        val deepLink = NotificationUtils.extractDeepLink(data)

        assertEquals("Should construct message deep link", "/messages/789", deepLink)
    }

    @Test
    fun `should use explicit deep link when provided`() {
        val data = NotificationData(
            type = "new_match",
            title = "New Match",
            body = "Match found",
            deepLink = "/custom/path",
            data = org.json.JSONObject("""{"match_id": 456}""")
        )

        val deepLink = NotificationUtils.extractDeepLink(data)

        assertEquals("Should use explicit deep link", "/custom/path", deepLink)
    }

    @Test
    fun `should return null for unknown notification type`() {
        val data = NotificationData(
            type = "unknown_type",
            title = "Unknown",
            body = "Unknown notification",
            deepLink = null,
            data = null
        )

        val deepLink = NotificationUtils.extractDeepLink(data)

        assertNull("Should return null for unknown type", deepLink)
    }
}

/**
 * Unit tests for TokenUtils
 */
class TokenUtilsTest {

    @Test
    fun `should validate correct JWT format`() {
        val validToken = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiMTIzIiwibmFtZSI6IkpvaG4ifQ.signature"

        assertTrue("Should validate JWT with 3 parts", TokenUtils.isValidJwtFormat(validToken))
    }

    @Test
    fun `should reject JWT with too few parts`() {
        val invalidToken = "header.payload"

        assertFalse("Should reject JWT with 2 parts", TokenUtils.isValidJwtFormat(invalidToken))
    }

    @Test
    fun `should reject JWT with empty part`() {
        val invalidToken = "header..signature"

        assertFalse("Should reject JWT with empty part", TokenUtils.isValidJwtFormat(invalidToken))
    }

    @Test
    fun `should extract user ID from valid JWT`() {
        // JWT with payload: {"user_id": "123", "name": "John"}
        val token = "header.eyJ1c2VyX2lkIjoiMTIzIiwibmFtZSI6IkpvaG4ifQ.signature"

        val userId = TokenUtils.extractUserIdFromJwt(token)

        assertEquals("Should extract user ID", "123", userId)
    }

    @Test
    fun `should return null for malformed JWT payload`() {
        val invalidToken = "header.not-base64-json.signature"

        val userId = TokenUtils.extractUserIdFromJwt(invalidToken)

        assertNull("Should return null for malformed payload", userId)
    }

    @Test
    fun `should sanitize token for logging`() {
        val token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiMTIzIiwibmFtZSI6IkpvaG4ifQ.signature-long-string"

        val sanitized = TokenUtils.sanitizeForLogging(token)

        assertTrue("Should show first 5 chars", sanitized.startsWith("eyJhb"))
        assertTrue("Should show last 5 chars", sanitized.endsWith("tring"))
        assertTrue("Should contain ellipsis", sanitized.contains("..."))
        assertTrue("Sanitized should be much shorter", sanitized.length < token.length)
    }

    @Test
    fun `should sanitize short token completely`() {
        val shortToken = "abc123"

        val sanitized = TokenUtils.sanitizeForLogging(shortToken)

        assertEquals("Should hide short tokens completely", "***", sanitized)
    }
}
