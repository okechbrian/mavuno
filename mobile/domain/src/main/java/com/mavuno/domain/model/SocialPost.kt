package com.mavuno.domain.model

data class SocialPost(
    val id: String,
    val farmId: String,
    val farmerName: String,
    val district: String,
    val crop: String,
    val body: String,
    val photoUrl: String?,
    val isVerified: Boolean,
    val yps: Int?,
    val createdAt: Long,
    val reactions: Map<String, Int>
)
