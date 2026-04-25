package com.mavuno.data.repository

import com.mavuno.data.local.dao.OfferDao
import com.mavuno.data.local.entity.toDomain
import com.mavuno.domain.model.Offer
import com.mavuno.domain.repository.MarketplaceRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject

class MarketplaceRepositoryImpl @Inject constructor(
    private val offerDao: OfferDao
) : MarketplaceRepository {
    override fun getOpenOffers(): Flow<List<Offer>> {
        return offerDao.getOpenOffers().map { entities ->
            entities.map { it.toDomain() }
        }
    }

    override suspend fun syncMarketplace() {
        // TODO: Fetch latest offers from web API
    }

    override suspend fun acceptOffer(offerId: String, buyerId: String) {
        offerDao.updateOfferStatus(offerId, "accepted")
        // TODO: Notify web API of the transaction
    }
}
