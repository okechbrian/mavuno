package com.mavuno.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.mavuno.data.local.entity.HardwarePingEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface HardwarePingDao {
    @Query("SELECT * FROM hardware_pings WHERE farmId = :farmId ORDER BY timestamp DESC")
    fun getPingsForFarm(farmId: String): Flow<List<HardwarePingEntity>>

    @Query("SELECT * FROM hardware_pings WHERE isSynced = 0")
    suspend fun getUnsyncedPings(): List<HardwarePingEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertPing(ping: HardwarePingEntity)

    @Query("UPDATE hardware_pings SET isSynced = 1 WHERE id IN (:pingIds)")
    suspend fun markPingsAsSynced(pingIds: List<String>)
}
