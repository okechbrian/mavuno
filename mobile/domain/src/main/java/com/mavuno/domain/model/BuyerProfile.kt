package com.mavuno.domain.model

data class BuyerProfile(
    val id: String,
    val name: String,
    val company: String,
    val region: String,
    val isVerified: Boolean,
    val totalVolumeKg: Int,
    val activeContracts: Int,
    val ectSpent: Double
)
