package com.mavuno.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey
import com.mavuno.domain.model.BatchPayment

@Entity(tableName = "batch_payments")
data class BatchPaymentEntity(
    @PrimaryKey val id: String,
    val buyerId: String,
    val timestamp: Long,
    val totalAmountUgx: Int,
    val offerCount: Int,
    val status: String,
    val paymentIds: List<String>
) {
    fun toDomain() = BatchPayment(
        id = id,
        timestamp = timestamp,
        totalAmountUgx = totalAmountUgx,
        offerCount = offerCount,
        status = status,
        paymentIds = paymentIds
    )
}

fun BatchPayment.toEntity(buyerId: String) = BatchPaymentEntity(
    id = id,
    buyerId = buyerId,
    timestamp = timestamp,
    totalAmountUgx = totalAmountUgx,
    offerCount = offerCount,
    status = status,
    paymentIds = paymentIds
)
