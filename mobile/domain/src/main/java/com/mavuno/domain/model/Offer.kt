package com.mavuno.domain.model

data class Offer(
    val id: String,
    val farmId: String,
    val farmerName: String,
    val crop: String,
    val quantityKg: Int,
    val floorPriceUgx: Int,
    val region: String,
    val status: String, // 'open', 'accepted', 'closed'
    val createdAt: Long,
    val paymentStatus: String? = null
)

data class Bid(
    val id: String,
    val offerId: String,
    val buyerId: String,
    val amountUgx: Int,
    val timestamp: Long
)
