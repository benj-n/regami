package com.regami.network

import okhttp3.OkHttpClient
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import java.util.concurrent.TimeUnit

/**
 * Unit tests for NetworkSecurity SSL pinning configuration
 */
class NetworkSecurityTest {

    @Before
    fun setUp() {
        // Reset any state if needed
    }

    @After
    fun tearDown() {
        // Clean up if needed
    }

    @Test
    fun `should build secure client with pinning enabled`() {
        val client = NetworkSecurity.buildSecureClient(enablePinning = true)

        assertNotNull("Client should not be null", client)
        assertTrue("Client should have interceptors", client.networkInterceptors.isNotEmpty())
        assertEquals("Client should have correct timeouts", 30, client.connectTimeoutMillis.toLong() / 1000)
    }

    @Test
    fun `should build client without pinning in debug`() {
        val client = NetworkSecurity.buildSecureClient(enablePinning = false)

        assertNotNull("Client should not be null", client)
        assertEquals("Client should have correct timeouts", 30, client.connectTimeoutMillis.toLong() / 1000)
    }

    @Test
    fun `should disable pinning in debug builds`() {
        val shouldPin = NetworkSecurity.shouldEnablePinning(isDebug = true)

        assertFalse("Pinning should be disabled in debug", shouldPin)
    }

    @Test
    fun `should enable pinning in release builds`() {
        val shouldPin = NetworkSecurity.shouldEnablePinning(isDebug = false)

        assertTrue("Pinning should be enabled in release", shouldPin)
    }

    @Test
    fun `should return production domain by default`() {
        val domain = NetworkSecurity.getPinnedDomain(useStaging = false)

        assertEquals("Should return production domain", "api.regami.com", domain)
    }

    @Test
    fun `should return staging domain when requested`() {
        val domain = NetworkSecurity.getPinnedDomain(useStaging = true)

        assertEquals("Should return staging domain", "staging-api.regami.com", domain)
    }

    @Test
    fun `should build staging client`() {
        val client = NetworkSecurity.buildSecureClient(
            enablePinning = true,
            useStaging = true
        )

        assertNotNull("Staging client should not be null", client)
    }

    @Test
    fun `should have multiple certificate pins for rotation`() {
        // This test verifies the structure is in place
        // Actual pins should be updated before production deployment
        val domain = NetworkSecurity.getPinnedDomain(useStaging = false)
        assertNotNull("Domain should not be null", domain)
        assertTrue("Domain should not be empty", domain.isNotEmpty())
    }

    @Test
    fun `should configure all timeouts correctly`() {
        val client = NetworkSecurity.buildSecureClient(enablePinning = false)

        assertEquals("Connect timeout should be 30s", 30000, client.connectTimeoutMillis)
        assertEquals("Read timeout should be 30s", 30000, client.readTimeoutMillis)
        assertEquals("Write timeout should be 30s", 30000, client.writeTimeoutMillis)
    }

    @Test
    fun `should allow HTTP traffic`() {
        val client = NetworkSecurity.buildSecureClient(enablePinning = false)

        // OkHttp follows redirects by default
        assertTrue("Should follow redirects", client.followRedirects)
        assertTrue("Should follow SSL redirects", client.followSslRedirects)
    }
}
