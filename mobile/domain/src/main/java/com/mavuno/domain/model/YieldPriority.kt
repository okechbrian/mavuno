package com.mavuno.domain.model

data class YieldPriority(
    val id: String,
    val farmId: String,
    val yps: Int,
    val kgAllocated: Int,
    val kgRemaining: Int,
    val aggregationPoint: String,
    val status: String, // 'active', 'expired', 'voided'
    val createdAt: Long,
    val expiresAt: Long,
    val signature: String
)
