package com.mavuno.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey
import com.mavuno.domain.model.Token

@Entity(tableName = "tokens")
data class TokenEntity(
    @PrimaryKey val id: String,
    val farmId: String,
    val yps: Int,
    val kwhAllocated: Int,
    val kwhRemaining: Int,
    val pumpNode: String,
    val status: String,
    val createdAt: Long,
    val expiresAt: Long,
    val signature: String
)

fun TokenEntity.toDomain() = Token(
    id = id,
    farmId = farmId,
    yps = yps,
    kwhAllocated = kwhAllocated,
    kwhRemaining = kwhRemaining,
    pumpNode = pumpNode,
    status = status,
    createdAt = createdAt,
    expiresAt = expiresAt,
    signature = signature
)

fun Token.toEntity() = TokenEntity(
    id = id,
    farmId = farmId,
    yps = yps,
    kwhAllocated = kwhAllocated,
    kwhRemaining = kwhRemaining,
    pumpNode = pumpNode,
    status = status,
    createdAt = createdAt,
    expiresAt = expiresAt,
    signature = signature
)
