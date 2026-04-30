package com.mavuno.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey
import com.mavuno.domain.model.YieldValue

@Entity(tableName = "ect_balances")
data class YieldValueEntity(
    @PrimaryKey val farmId: String,
    val balance: Double,
    val lastUpdated: Long
)

fun YieldValueEntity.toDomain() = YieldValue(
    farmId = farmId,
    balance = balance,
    lastUpdated = lastUpdated
)

fun YieldValue.toEntity() = YieldValueEntity(
    farmId = farmId,
    balance = balance,
    lastUpdated = lastUpdated
)

