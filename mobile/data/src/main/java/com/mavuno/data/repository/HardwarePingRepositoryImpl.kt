package com.mavuno.data.repository

import com.mavuno.data.local.dao.HardwarePingDao
import com.mavuno.data.local.entity.toDomain
import com.mavuno.data.local.entity.toEntity
import com.mavuno.data.remote.MavunoApi
import com.mavuno.data.remote.model.TelemetryRequest
import com.mavuno.domain.model.HardwarePing
import com.mavuno.domain.repository.HardwarePingRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject

class HardwarePingRepositoryImpl @Inject constructor(
    private val dao: HardwarePingDao,
    private val api: MavunoApi
) : HardwarePingRepository {
    override fun getPingsForFarm(farmId: String): Flow<List<HardwarePing>> {
        return dao.getPingsForFarm(farmId).map { entities ->
            entities.map { it.toDomain() }
        }
    }

    override suspend fun savePingLocally(ping: HardwarePing) {
        dao.insertPing(ping.toEntity().copy(isSynced = false))
    }

    override suspend fun syncUnsyncedPings() {
        val unsynced = dao.getUnsyncedPings()
        if (unsynced.isEmpty()) return

        for (ping in unsynced) {
            try {
                val response = api.sendTelemetry(
                    TelemetryRequest(
                        farm_id = ping.farmId,
                        soil_moisture = ping.soilMoisture,
                        temp_c = ping.soilTemperature,
                        rainfall_mm = ping.rainfall,
                        humidity_pct = ping.ambientHumidity,
                        n_mg_kg = ping.nitrogen,
                        p_mg_kg = ping.phosphorus,
                        k_mg_kg = ping.potassium
                    )
                )
                if (response.isSuccessful) {
                    dao.markPingsAsSynced(listOf(ping.id))
                }
            } catch (e: Exception) {
                // Network error, skip for now
            }
        }
    }
}
