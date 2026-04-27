package com.mavuno.domain.repository

import com.mavuno.domain.model.BatchPayment
import com.mavuno.domain.model.BuyerProfile
import kotlinx.coroutines.flow.Flow

interface BuyerRepository {
    fun getBuyerProfile(buyerId: String): Flow<BuyerProfile?>
    fun getBatchPayments(buyerId: String): Flow<List<BatchPayment>>
    suspend fun syncBuyerData(buyerId: String)
}
