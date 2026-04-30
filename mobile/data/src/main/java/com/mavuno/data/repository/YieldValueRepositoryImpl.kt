package com.mavuno.data.repository

import com.mavuno.data.local.dao.YieldValueDao
import com.mavuno.data.local.entity.YieldValueEntity
import com.mavuno.data.local.entity.toDomain
import com.mavuno.data.remote.MavunoApi
import com.mavuno.domain.model.YieldValue
import com.mavuno.domain.repository.YieldValueRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject

class YieldValueRepositoryImpl @Inject constructor(
    private val dao: YieldValueDao,
    private val api: MavunoApi
) : YieldValueRepository {
    override fun getBalanceForFarm(farmId: String): Flow<YieldValue?> {
        return dao.getBalanceForFarm(farmId).map { it?.toDomain() }
    }

    override suspend fun syncBalance(farmId: String) {
        try {
            val response = api.getYieldValue(farmId)
            if (response.isSuccessful) {
                response.body()?.let { remote ->
                    dao.insertBalance(
                        YieldValueEntity(
                            farmId = remote.farm_id,
                            balance = remote.balance,
                            lastUpdated = System.currentTimeMillis()
                        )
                    )
                }
            }
        } catch (e: Exception) {
            // Offline
        }
    }
}

