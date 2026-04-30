package com.mavuno.data.repository

import com.mavuno.data.local.dao.YieldPriorityDao
import com.mavuno.data.local.entity.toDomain
import com.mavuno.data.local.entity.toEntity
import com.mavuno.domain.model.YieldPriority
import com.mavuno.domain.repository.YieldPriorityRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject

class YieldPriorityRepositoryImpl @Inject constructor(
    private val dao: YieldPriorityDao
) : YieldPriorityRepository {
    override fun getYieldPrioritiesForFarm(farmId: String): Flow<List<YieldPriority>> {
        return dao.getYieldPrioritiesForFarm(farmId).map { entities ->
            entities.map { it.toDomain() }
        }
    }

    override suspend fun saveYieldPriorityLocally(yieldPriority: YieldPriority) {
        dao.insertYieldPriority(yieldPriority.toEntity())
    }

    override suspend fun syncYieldPriorities() {
        // TODO: Sync newly created yield priorities to the global ledger
    }
}
