package com.regami.network

import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebView
import android.webkit.WebViewClient
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.IOException

/**
 * Secure WebView client with SSL pinning for external requests
 * Intercepts network requests and routes them through OkHttp with certificate pinning
 */
class SecureWebViewClient(
    private val okHttpClient: OkHttpClient,
    private val onPageStarted: ((String) -> Unit)? = null,
    private val onPageFinished: ((String) -> Unit)? = null,
    private val onError: ((String) -> Unit)? = null
) : WebViewClient() {

    companion object {
        private const val TAG = "SecureWebViewClient"
    }

    override fun onPageStarted(view: WebView?, url: String?, favicon: android.graphics.Bitmap?) {
        super.onPageStarted(view, url, favicon)
        url?.let { onPageStarted?.invoke(it) }
    }

    override fun onPageFinished(view: WebView?, url: String?) {
        super.onPageFinished(view, url)
        url?.let { onPageFinished?.invoke(it) }
    }

    override fun onReceivedError(
        view: WebView?,
        request: WebResourceRequest?,
        error: android.webkit.WebResourceError?
    ) {
        super.onReceivedError(view, request, error)
        if (request?.isForMainFrame == true) {
            val errorMessage = error?.description?.toString() ?: "Unknown error"
            onError?.invoke(errorMessage)
        }
    }

    /**
     * Intercept resource requests for specific domains and route through OkHttp
     * This enables SSL pinning for API requests made from WebView
     *
     * Note: Intercepting ALL requests can impact performance. Only intercept
     * requests to domains that need certificate pinning (e.g., your API domain)
     */
    override fun shouldInterceptRequest(
        view: WebView?,
        request: WebResourceRequest?
    ): WebResourceResponse? {
        request?.url?.let { uri ->
            val urlString = uri.toString()

            // Only intercept requests to our API domain
            // Adjust this condition based on your needs
            if (shouldIntercept(urlString)) {
                return try {
                    interceptWithOkHttp(urlString, request)
                } catch (e: IOException) {
                    android.util.Log.e(TAG, "Error intercepting request: $urlString", e)
                    null // Fall back to default WebView handling
                } catch (e: Exception) {
                    android.util.Log.e(TAG, "Unexpected error intercepting request", e)
                    null
                }
            }
        }

        return super.shouldInterceptRequest(view, request)
    }

    /**
     * Determine if a URL should be intercepted and routed through OkHttp
     * Override this method to customize which requests use SSL pinning
     *
     * @param url The URL to check
     * @return True if the request should be intercepted
     */
    protected open fun shouldIntercept(url: String): Boolean {
        // By default, intercept requests to our API domain
        // Modify this based on your specific requirements
        val pinnedDomain = NetworkSecurity.getPinnedDomain()
        return url.contains(pinnedDomain)
    }

    /**
     * Intercept a request and execute it through OkHttp with SSL pinning
     *
     * @param url The URL to request
     * @param webRequest The original WebView request
     * @return WebResourceResponse to return to WebView
     */
    private fun interceptWithOkHttp(
        url: String,
        webRequest: WebResourceRequest
    ): WebResourceResponse? {
        val requestBuilder = Request.Builder().url(url)

        // Copy headers from WebView request
        webRequest.requestHeaders?.forEach { (key, value) ->
            requestBuilder.addHeader(key, value)
        }

        val request = requestBuilder.build()
        val response = okHttpClient.newCall(request).execute()

        if (!response.isSuccessful) {
            android.util.Log.w(TAG, "Request failed: ${response.code} for $url")
            return null
        }

        val body = response.body ?: return null
        val contentType = response.header("Content-Type") ?: "text/html"
        val encoding = response.header("Content-Encoding")

        // Parse content type to get MIME type and charset
        val parts = contentType.split(";")
        val mimeType = parts.getOrNull(0)?.trim() ?: "text/html"
        val charset = parts.getOrNull(1)?.trim()
            ?.removePrefix("charset=")
            ?.trim() ?: "UTF-8"

        return WebResourceResponse(
            mimeType,
            charset,
            response.code,
            response.message,
            response.headers.toMultimap().mapValues { it.value.firstOrNull() ?: "" },
            body.byteStream()
        )
    }
}
