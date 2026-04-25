package com.mavuno.data.di

import android.app.Application
import androidx.room.Room
import com.mavuno.data.local.MavunoDatabase
import com.mavuno.data.local.dao.*
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object DatabaseModule {

    @Provides
    @Singleton
    fun provideMavunoDatabase(app: Application): MavunoDatabase {
        return Room.databaseBuilder(
            app,
            MavunoDatabase::class.java,
            MavunoDatabase.DATABASE_NAME
        ).build()
    }

    @Provides
    @Singleton
    fun provideFarmerDao(db: MavunoDatabase): FarmerDao = db.farmerDao

    @Provides
    @Singleton
    fun provideBuyerDao(db: MavunoDatabase): BuyerDao = db.buyerDao

    @Provides
    @Singleton
    fun provideHardwarePingDao(db: MavunoDatabase): HardwarePingDao = db.hardwarePingDao

    @Provides
    @Singleton
    fun provideEctBalanceDao(db: MavunoDatabase): EctBalanceDao = db.ectBalanceDao

    @Provides
    @Singleton
    fun provideTokenDao(db: MavunoDatabase): TokenDao = db.tokenDao

    @Provides
    @Singleton
    fun provideOfferDao(db: MavunoDatabase): OfferDao = db.offerDao
}
