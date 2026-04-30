package com.mavuno.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.mavuno.data.local.entity.YieldPriorityEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface YieldPriorityDao {
    @Query("SELECT * FROM yield_priorities WHERE farmId = :farmId ORDER BY createdAt DESC")
    fun getYieldPrioritiesForFarm(farmId: String): Flow<List<YieldPriorityEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertYieldPriority(yieldPriority: YieldPriorityEntity)

    @Query("UPDATE yield_priorities SET status = :status WHERE id = :id")
    suspend fun updateYieldPriorityStatus(id: String, status: String)
}
