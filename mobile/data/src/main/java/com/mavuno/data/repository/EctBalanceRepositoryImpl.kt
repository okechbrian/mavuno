package com.mavuno.data.repository

import com.mavuno.data.local.dao.EctBalanceDao
import com.mavuno.data.local.entity.EctBalanceEntity
import com.mavuno.data.local.entity.toDomain
import com.mavuno.data.remote.MavunoApi
import com.mavuno.domain.model.EctBalance
import com.mavuno.domain.repository.EctBalanceRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject

class EctBalanceRepositoryImpl @Inject constructor(
    private val dao: EctBalanceDao,
    private val api: MavunoApi
) : EctBalanceRepository {
    override fun getBalanceForFarm(farmId: String): Flow<EctBalance?> {
        return dao.getBalanceForFarm(farmId).map { it?.toDomain() }
    }

    override suspend fun syncBalance(farmId: String) {
        try {
            val response = api.getEctBalance(farmId)
            if (response.isSuccessful) {
                response.body()?.let { remote ->
                    dao.insertBalance(
                        EctBalanceEntity(
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
