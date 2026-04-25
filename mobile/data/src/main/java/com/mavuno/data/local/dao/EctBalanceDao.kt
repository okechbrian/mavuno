package com.mavuno.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.mavuno.data.local.entity.EctBalanceEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface EctBalanceDao {
    @Query("SELECT * FROM ect_balances WHERE farmId = :farmId")
    fun getBalanceForFarm(farmId: String): Flow<EctBalanceEntity?>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertBalance(balance: EctBalanceEntity)
}
