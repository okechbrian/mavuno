package com.mavuno.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey
import com.mavuno.domain.model.Offer

@Entity(tableName = "offers")
data class OfferEntity(
    @PrimaryKey val id: String,
    val farmId: String,
    val farmerName: String,
    val crop: String,
    val quantityKg: Int,
    val floorPriceUgx: Int,
    val region: String,
    val status: String,
    val createdAt: Long,
    val paymentStatus: String?
)

fun OfferEntity.toDomain() = Offer(
    id = id,
    farmId = farmId,
    farmerName = farmerName,
    crop = crop,
    quantityKg = quantityKg,
    floorPriceUgx = floorPriceUgx,
    region = region,
    status = status,
    createdAt = createdAt,
    paymentStatus = paymentStatus
)

fun Offer.toEntity() = OfferEntity(
    id = id,
    farmId = farmId,
    farmerName = farmerName,
    crop = crop,
    quantityKg = quantityKg,
    floorPriceUgx = floorPriceUgx,
    region = region,
    status = status,
    createdAt = createdAt,
    paymentStatus = paymentStatus
)
