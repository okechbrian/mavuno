package com.mavuno.features.verification

import android.util.Base64
import javax.inject.Inject
import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec

class TokenVerifier @Inject constructor() {

    private val SECRET = "MAVUNO_OFFLINE_SECRET_2026"

    /**
     * Verifies a token's HMAC-SHA256 signature offline.
     * Token format expected: "farmId|yps|kwh|pumpNode|expiresAt|signature"
     */
    fun verifyToken(scannedData: String): VerificationResult {
        val parts = scannedData.split("|")
        if (parts.size < 6) return VerificationResult.Invalid("Malformed token format")

        val farmId = parts[0]
        val yps = parts[1]
        val kwh = parts[2]
        val pumpNode = parts[3]
        val expiresAtStr = parts[4]
        val providedSignature = parts[5]

        val expiresAt = expiresAtStr.toLongOrNull() ?: 0
        if (System.currentTimeMillis() > expiresAt) {
            return VerificationResult.Expired
        }

        val payload = "$farmId|$yps|$kwh|$pumpNode|$expiresAt"
        val expectedSignature = sign(payload, SECRET)

        return if (providedSignature == expectedSignature) {
            VerificationResult.Success(farmId, kwh.toInt())
        } else {
            VerificationResult.Invalid("Cryptographic signature mismatch")
        }
    }

    private fun sign(data: String, secret: String): String {
        return try {
            val sha256Hmac = Mac.getInstance("HmacSHA256")
            val secretKey = SecretKeySpec(secret.toByteArray(), "HmacSHA256")
            sha256Hmac.init(secretKey)
            val signedBytes = sha256Hmac.doFinal(data.toByteArray())
            Base64.encodeToString(signedBytes, Base64.NO_WRAP)
        } catch (e: Exception) {
            ""
        }
    }
}

sealed class VerificationResult {
    data class Success(val farmId: String, val kwh: Int) : VerificationResult()
    data class Invalid(val reason: String) : VerificationResult()
    object Expired : VerificationResult()
}
