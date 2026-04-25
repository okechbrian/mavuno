package com.mavuno.domain.repository

import com.mavuno.domain.model.Offer
import kotlinx.coroutines.flow.Flow

interface MarketplaceRepository {
    fun getOpenOffers(): Flow<List<Offer>>
    suspend fun syncMarketplace()
    suspend fun acceptOffer(offerId: String, buyerId: String)
}
