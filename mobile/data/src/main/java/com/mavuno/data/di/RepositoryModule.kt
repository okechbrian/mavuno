package com.mavuno.data.di

import com.mavuno.data.repository.*
import com.mavuno.domain.repository.*
import dagger.Binds
import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
abstract class RepositoryModule {

    @Binds
    @Singleton
    abstract fun bindFarmerRepository(
        impl: FarmerRepositoryImpl
    ): FarmerRepository

    @Binds
    @Singleton
    abstract fun bindBuyerRepository(
        impl: BuyerRepositoryImpl
    ): BuyerRepository

    @Binds
    @Singleton
    abstract fun bindHardwarePingRepository(
        impl: HardwarePingRepositoryImpl
    ): HardwarePingRepository

    @Binds
    @Singleton
    abstract fun bindEctBalanceRepository(
        impl: EctBalanceRepositoryImpl
    ): EctBalanceRepository

    @Binds
    @Singleton
    abstract fun bindTokenRepository(
        impl: TokenRepositoryImpl
    ): TokenRepository

    @Binds
    @Singleton
    abstract fun bindMarketplaceRepository(
        impl: MarketplaceRepositoryImpl
    ): MarketplaceRepository
}
