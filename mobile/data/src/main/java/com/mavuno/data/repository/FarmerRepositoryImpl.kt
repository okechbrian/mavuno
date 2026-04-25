package com.mavuno.data.repository

import com.mavuno.data.local.dao.FarmerDao
import com.mavuno.data.local.entity.toDomain
import com.mavuno.data.remote.MavunoApi
import com.mavuno.domain.model.Farmer
import com.mavuno.domain.repository.FarmerRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject

class FarmerRepositoryImpl @Inject constructor(
    private val dao: FarmerDao,
    private val api: MavunoApi
) : FarmerRepository {
    override fun getAllFarmers(): Flow<List<Farmer>> {
        return dao.getAllFarmers().map { entities ->
            entities.map { it.toDomain() }
        }
    }

    override fun getFarmerById(farmId: String): Flow<Farmer?> {
        return dao.getFarmerById(farmId).map { it?.toDomain() }
    }

    override suspend fun syncFarmers() {
        // In a real app, we'd fetch from /farms and update Room
        // For the prototype, we'll focus on individual data points (scores, balances)
    }
}
