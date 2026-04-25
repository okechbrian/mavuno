package com.mavuno.domain.model

data class Token(
    val id: String,
    val farmId: String,
    val yps: Int,
    val kwhAllocated: Int,
    val kwhRemaining: Int,
    val pumpNode: String,
    val status: String, // 'active', 'expired', 'voided'
    val createdAt: Long,
    val expiresAt: Long,
    val signature: String
)
