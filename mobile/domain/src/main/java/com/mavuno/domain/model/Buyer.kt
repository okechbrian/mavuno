package com.mavuno.domain.model

data class Buyer(
    val buyerId: String,
    val name: String,
    val region: String,
    val phoneNumber: String,
    val cropsPurchased: List<String>,
    val floorPrice: Double
)
