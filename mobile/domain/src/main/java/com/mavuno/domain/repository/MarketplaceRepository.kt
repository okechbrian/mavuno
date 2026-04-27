package com.mavuno.domain.repository

import com.mavuno.domain.model.MarketPrices
import com.mavuno.domain.model.Offer
import kotlinx.coroutines.flow.Flow

interface MarketplaceRepository {
    fun getOpenOffers(): Flow<List<Offer>>
    suspend fun syncMarketplace()
    suspend fun placeBid(offerId: String, msisdn: String): Flow<Boolean>
    suspend fun getMarketPrices(crop: String, region: String): MarketPrices
}
