package com.mavuno.domain.repository

import com.mavuno.domain.model.Farmer
import kotlinx.coroutines.flow.Flow

interface FarmerRepository {
    fun getAllFarmers(): Flow<List<Farmer>>
    fun getFarmerById(farmId: String): Flow<Farmer?>
    suspend fun syncFarmers() // Placeholder for API sync
}
