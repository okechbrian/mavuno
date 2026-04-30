package com.mavuno.features.verification

import javax.inject.Inject

/**
 * Validates cryptographically signed yield priorities.
 */
class YieldPriorityVerifier @Inject constructor() {

    private val SECRET = "future-makers-hackathon-2026-secret-key"

    /**
     * Priority format expected: "farmId|yps|kg|aggregationPoint|expiresAt|signature"
     */
    fun verify(scannedData: String): VerificationResult {
        val parts = scannedData.split("|")
        if (parts.size != 6) return VerificationResult.InvalidFormat

        val farmId = parts[0]
        val yps = parts[1]
        val kg = parts[2]
        val aggregationPoint = parts[3]
        val expiresAt = parts[4]
        val providedSignature = parts[5]

        val payload = "$farmId|$yps|$kg|$aggregationPoint|$expiresAt"
        val expectedSignature = sign(payload, SECRET)

        return if (providedSignature == expectedSignature) {
            VerificationResult.Success(farmId, kg.toInt())
        } else {
            VerificationResult.InvalidSignature
        }
    }

    private fun sign(data: String, secret: String): String {
        // Mock implementation of HMAC-SHA256
        return "SIG_" + (data + secret).hashCode().toString()
    }

    sealed class VerificationResult {
        data class Success(val farmId: String, val kg: Int) : VerificationResult()
        object InvalidFormat : VerificationResult()
        object InvalidSignature : VerificationResult()
        object Expired : VerificationResult()
    }
}
