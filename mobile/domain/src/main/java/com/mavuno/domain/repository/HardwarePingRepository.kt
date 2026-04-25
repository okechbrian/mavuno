package com.mavuno.domain.repository

import com.mavuno.domain.model.HardwarePing
import kotlinx.coroutines.flow.Flow

interface HardwarePingRepository {
    fun getPingsForFarm(farmId: String): Flow<List<HardwarePing>>
    suspend fun savePingLocally(ping: HardwarePing)
    suspend fun syncUnsyncedPings()
}
