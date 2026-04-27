package com.mavuno.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey
import com.mavuno.domain.model.BuyerProfile

@Entity(tableName = "buyer_profiles")
data class BuyerProfileEntity(
    @PrimaryKey val id: String,
    val name: String,
    val company: String,
    val region: String,
    val isVerified: Boolean,
    val totalVolumeKg: Int,
    val activeContracts: Int,
    val ectSpent: Double
) {
    fun toDomain() = BuyerProfile(
        id = id,
        name = name,
        company = company,
        region = region,
        isVerified = isVerified,
        totalVolumeKg = totalVolumeKg,
        activeContracts = activeContracts,
        ectSpent = ectSpent
    )
}

fun BuyerProfile.toEntity() = BuyerProfileEntity(
    id = id,
    name = name,
    company = company,
    region = region,
    isVerified = isVerified,
    totalVolumeKg = totalVolumeKg,
    activeContracts = activeContracts,
    ectSpent = ectSpent
)
