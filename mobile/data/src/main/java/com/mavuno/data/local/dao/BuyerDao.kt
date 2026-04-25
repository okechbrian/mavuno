package com.mavuno.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.mavuno.data.local.entity.BuyerEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface BuyerDao {
    @Query("SELECT * FROM buyers")
    fun getAllBuyers(): Flow<List<BuyerEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertBuyers(buyers: List<BuyerEntity>)

    @Query("DELETE FROM buyers")
    suspend fun clearAllBuyers()
}
