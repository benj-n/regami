package com.regami.network

import okhttp3.CertificatePinner
import okhttp3.OkHttpClient
import java.util.concurrent.TimeUnit

/**
 * Network security configuration with SSL certificate pinning
 * Prevents Man-in-the-Middle (MITM) attacks by pinning production API certificates
 */
object NetworkSecurity {

    /**
     * Production API domain
     * Update this with your actual production domain
     */
    private const val PRODUCTION_DOMAIN = "api.regami.com"

    /**
     * Certificate pins for production API
     *
     * Generate pins using:
     * openssl s_client -servername api.regami.com -connect api.regami.com:443 | \
     *   openssl x509 -pubkey -noout | \
     *   openssl pkey -pubin -outform der | \
     *   openssl dgst -sha256 -binary | \
     *   openssl enc -base64
     *
     * IMPORTANT: Include multiple pins for certificate rotation:
     * - Current certificate pin
     * - Backup certificate pin (for rotation)
     * - Root CA certificate pin (fallback)
     */
    private val PRODUCTION_PINS = arrayOf(
        // Primary certificate (update with actual SHA-256 hash)
        "sha256/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
        // Backup certificate for rotation (update with actual SHA-256 hash)
        "sha256/BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB=",
        // Root CA pin (Let's Encrypt, DigiCert, etc.)
        "sha256/CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC="
    )

    /**
     * Staging API domain (if you have one)
     */
    private const val STAGING_DOMAIN = "staging-api.regami.com"

    /**
     * Certificate pins for staging API
     */
    private val STAGING_PINS = arrayOf(
        "sha256/DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD=",
        "sha256/EEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE="
    )

    /**
     * Build OkHttpClient with certificate pinning
     *
     * @param enablePinning Whether to enable certificate pinning (disable for debug builds)
     * @param useStaging Whether to use staging environment pins
     * @return Configured OkHttpClient instance
     */
    fun buildSecureClient(
        enablePinning: Boolean = true,
        useStaging: Boolean = false
    ): OkHttpClient {
        val builder = OkHttpClient.Builder()
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)

        if (enablePinning) {
            val pinnerBuilder = CertificatePinner.Builder()

            if (useStaging) {
                // Add staging pins
                STAGING_PINS.forEach { pin ->
                    pinnerBuilder.add(STAGING_DOMAIN, pin)
                }
            } else {
                // Add production pins
                PRODUCTION_PINS.forEach { pin ->
                    pinnerBuilder.add(PRODUCTION_DOMAIN, pin)
                }
            }

            builder.certificatePinner(pinnerBuilder.build())
        }

        return builder.build()
    }

    /**
     * Check if SSL pinning is enabled
     * Pinning should be disabled in debug builds to allow testing with local servers
     *
     * @param isDebug Whether this is a debug build
     * @return True if pinning should be enabled
     */
    fun shouldEnablePinning(isDebug: Boolean): Boolean {
        return !isDebug
    }

    /**
     * Get the pinned domain for current environment
     *
     * @param useStaging Whether to use staging environment
     * @return Domain name that is pinned
     */
    fun getPinnedDomain(useStaging: Boolean = false): String {
        return if (useStaging) STAGING_DOMAIN else PRODUCTION_DOMAIN
    }
}
