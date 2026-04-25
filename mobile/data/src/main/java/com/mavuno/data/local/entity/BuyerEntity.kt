package com.mavuno.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey
import com.mavuno.domain.model.Buyer

@Entity(tableName = "buyers")
data class BuyerEntity(
    @PrimaryKey val buyerId: String,
    val name: String,
    val region: String,
    val phoneNumber: String,
    val cropsPurchased: List<String>,
    val floorPrice: Double
)

fun BuyerEntity.toDomain() = Buyer(
    buyerId = buyerId,
    name = name,
    region = region,
    phoneNumber = phoneNumber,
    cropsPurchased = cropsPurchased,
    floorPrice = floorPrice
)

fun Buyer.toEntity() = BuyerEntity(
    buyerId = buyerId,
    name = name,
    region = region,
    phoneNumber = phoneNumber,
    cropsPurchased = cropsPurchased,
    floorPrice = floorPrice
)
