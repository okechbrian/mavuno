package com.mavuno.domain.model

data class BatchPayment(
    val id: String,
    val timestamp: Long,
    val totalAmountUgx: Int,
    val offerCount: Int,
    val status: String, // "Settled", "Pending", "Failed"
    val paymentIds: List<String>
)
