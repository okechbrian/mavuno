package com.mavuno.data.local

import androidx.room.Database
import androidx.room.RoomDatabase
import androidx.room.TypeConverters
import com.mavuno.data.local.dao.*
import com.mavuno.data.local.entity.*

@Database(
    entities = [
        FarmerEntity::class,
        HardwarePingEntity::class,
        EctBalanceEntity::class,
        TokenEntity::class,
        OfferEntity::class,
        SocialPostEntity::class,
        TrainingModuleEntity::class,
        BuyerProfileEntity::class,
        BatchPaymentEntity::class
    ],
    version = 4,
    exportSchema = false
)
@TypeConverters(Converters::class)
abstract class MavunoDatabase : RoomDatabase() {
    abstract val farmerDao: FarmerDao
    abstract val buyerDao: BuyerDao
    abstract val hardwarePingDao: HardwarePingDao
    abstract val ectBalanceDao: EctBalanceDao
    abstract val tokenDao: TokenDao
    abstract val offerDao: OfferDao
    abstract val socialDao: SocialDao
    abstract val trainingDao: TrainingDao

    companion object {
        const val DATABASE_NAME = "mavuno_db"
    }
}
