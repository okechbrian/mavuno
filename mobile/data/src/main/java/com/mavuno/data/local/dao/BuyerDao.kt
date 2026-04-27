package com.mavuno.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.mavuno.data.local.entity.BatchPaymentEntity
import com.mavuno.data.local.entity.BuyerProfileEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface BuyerDao {
    @Query("SELECT * FROM buyer_profiles WHERE id = :id LIMIT 1")
    fun observeProfile(id: String): Flow<BuyerProfileEntity?>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertProfile(profile: BuyerProfileEntity)

    @Query("SELECT * FROM batch_payments WHERE buyerId = :buyerId ORDER BY timestamp DESC")
    fun observeBatchPayments(buyerId: String): Flow<List<BatchPaymentEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertBatchPayments(payments: List<BatchPaymentEntity>)

    @Query("DELETE FROM buyer_profiles WHERE id = :id")
    suspend fun deleteProfile(id: String)
}
