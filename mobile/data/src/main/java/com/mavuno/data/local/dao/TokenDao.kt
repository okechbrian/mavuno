package com.mavuno.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.mavuno.data.local.entity.TokenEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface TokenDao {
    @Query("SELECT * FROM tokens WHERE farmId = :farmId ORDER BY createdAt DESC")
    fun getTokensForFarm(farmId: String): Flow<List<TokenEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertToken(token: TokenEntity)

    @Query("UPDATE tokens SET status = :status WHERE id = :tokenId")
    suspend fun updateTokenStatus(tokenId: String, status: String)
}
