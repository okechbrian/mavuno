package com.mavuno.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.mavuno.data.local.entity.YieldValueEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface YieldValueDao {
    @Query("SELECT * FROM ect_balances WHERE farmId = :farmId")
    fun getBalanceForFarm(farmId: String): Flow<YieldValueEntity?>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertBalance(balance: YieldValueEntity)
}

