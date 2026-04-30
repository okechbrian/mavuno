package com.mavuno.domain.repository

import com.mavuno.domain.model.YieldValue
import kotlinx.coroutines.flow.Flow

interface YieldValueRepository {
    fun getBalanceForFarm(farmId: String): Flow<YieldValue?>
    suspend fun syncBalance(farmId: String)
}

