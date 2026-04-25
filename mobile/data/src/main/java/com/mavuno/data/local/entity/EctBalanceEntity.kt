package com.mavuno.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey
import com.mavuno.domain.model.EctBalance

@Entity(tableName = "ect_balances")
data class EctBalanceEntity(
    @PrimaryKey val farmId: String,
    val balance: Double,
    val lastUpdated: Long
)

fun EctBalanceEntity.toDomain() = EctBalance(
    farmId = farmId,
    balance = balance,
    lastUpdated = lastUpdated
)

fun EctBalance.toEntity() = EctBalanceEntity(
    farmId = farmId,
    balance = balance,
    lastUpdated = lastUpdated
)
