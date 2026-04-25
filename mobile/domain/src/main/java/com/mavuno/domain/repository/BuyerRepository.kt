package com.mavuno.domain.repository

import com.mavuno.domain.model.Buyer
import kotlinx.coroutines.flow.Flow

interface BuyerRepository {
    fun getAllBuyers(): Flow<List<Buyer>>
    suspend fun syncBuyers() // Placeholder for API sync
}
