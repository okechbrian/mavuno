package com.mavuno.domain.repository

import com.mavuno.domain.model.YieldPriority
import kotlinx.coroutines.flow.Flow

interface YieldPriorityRepository {
    fun getYieldPrioritiesForFarm(farmId: String): Flow<List<YieldPriority>>
    suspend fun saveYieldPriorityLocally(yieldPriority: YieldPriority)
    suspend fun syncYieldPriorities()
}
