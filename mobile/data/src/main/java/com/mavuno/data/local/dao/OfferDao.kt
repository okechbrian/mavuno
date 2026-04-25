package com.mavuno.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.mavuno.data.local.entity.OfferEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface OfferDao {
    @Query("SELECT * FROM offers WHERE status = 'open' ORDER BY createdAt DESC")
    fun getOpenOffers(): Flow<List<OfferEntity>>

    @Query("SELECT * FROM offers WHERE farmId = :farmId")
    fun getOffersForFarmer(farmId: String): Flow<List<OfferEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertOffers(offers: List<OfferEntity>)

    @Query("UPDATE offers SET status = :status WHERE id = :offerId")
    suspend fun updateOfferStatus(offerId: String, status: String)
}
