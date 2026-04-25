package com.mavuno.domain.repository

import com.mavuno.domain.model.EctBalance
import kotlinx.coroutines.flow.Flow

interface EctBalanceRepository {
    fun getBalanceForFarm(farmId: String): Flow<EctBalance?>
    suspend fun syncBalance(farmId: String)
}
