package com.mavuno.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey
import com.mavuno.domain.model.Farmer

@Entity(tableName = "farmers")
data class FarmerEntity(
    @PrimaryKey val farmId: String,
    val name: String,
    val region: String,
    val phoneNumber: String,
    val mainCrop: String,
    val ypsScore: Int
)

fun FarmerEntity.toDomain() = Farmer(
    farmId = farmId,
    name = name,
    region = region,
    phoneNumber = phoneNumber,
    mainCrop = mainCrop,
    ypsScore = ypsScore
)

fun Farmer.toEntity() = FarmerEntity(
    farmId = farmId,
    name = name,
    region = region,
    phoneNumber = phoneNumber,
    mainCrop = mainCrop,
    ypsScore = ypsScore
)
