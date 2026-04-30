package com.mavuno.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey
import com.mavuno.domain.model.YieldPriority

@Entity(tableName = "yield_priorities")
data class YieldPriorityEntity(
    @PrimaryKey val id: String,
    val farmId: String,
    val yps: Int,
    val kgAllocated: Int,
    val kgRemaining: Int,
    val aggregationPoint: String,
    val status: String,
    val createdAt: Long,
    val expiresAt: Long,
    val signature: String
)

fun YieldPriorityEntity.toDomain() = YieldPriority(
    id = id,
    farmId = farmId,
    yps = yps,
    kgAllocated = kgAllocated,
    kgRemaining = kgRemaining,
    aggregationPoint = aggregationPoint,
    status = status,
    createdAt = createdAt,
    expiresAt = expiresAt,
    signature = signature
)

fun YieldPriority.toEntity() = YieldPriorityEntity(
    id = id,
    farmId = farmId,
    yps = yps,
    kgAllocated = kgAllocated,
    kgRemaining = kgRemaining,
    aggregationPoint = aggregationPoint,
    status = status,
    createdAt = createdAt,
    expiresAt = expiresAt,
    signature = signature
)
