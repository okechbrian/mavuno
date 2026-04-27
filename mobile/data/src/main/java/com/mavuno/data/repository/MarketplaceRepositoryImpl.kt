package com.mavuno.data.repository

import android.util.Log
import com.mavuno.data.local.dao.OfferDao
import com.mavuno.data.local.entity.OfferEntity
import com.mavuno.data.local.entity.toDomain
import com.mavuno.data.remote.MavunoApi
import com.mavuno.domain.model.MarketPrices
import com.mavuno.domain.model.Offer
import com.mavuno.domain.model.PriceSeriesPoint
import com.mavuno.domain.repository.MarketplaceRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.emitAll
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.onStart
import javax.inject.Inject

class MarketplaceRepositoryImpl @Inject constructor(
    private val offerDao: OfferDao,
    private val api: MavunoApi
) : MarketplaceRepository {

    override fun getOpenOffers(): Flow<List<Offer>> = flow {
        emitAll(
            offerDao.getOpenOffers().map { entities ->
                entities.map { it.toDomain() }
            }.onStart {
                // Sync on background thread, ignore emit in flow pipeline
                try {
                    syncMarketplace()
                } catch (e: Exception) {
                    // Handled inside syncMarketplace
                }
            }
        )
    }

    override suspend fun syncMarketplace() {
        try {
            val response = api.getOffers()
            if (response.isSuccessful) {
                val offersMap = response.body() ?: emptyMap()
                val entities = offersMap.values.flatten().map { dto ->
                    OfferEntity(
                        id = dto.id,
                        farmId = dto.farmId,
                        farmerName = dto.farmerName,
                        crop = dto.crop,
                        quantityKg = dto.quantityKg,
                        floorPriceUgx = dto.floorPriceUgx,
                        region = dto.region,
                        status = dto.status,
                        createdAt = dto.createdAt,
                        paymentStatus = dto.paymentStatus
                    )
                }
                
                if (entities.isNotEmpty()) {
                    offerDao.insertOffers(entities)
                }
            } else {
                Log.e("MarketplaceRepo", "API Sync Error: ${response.code()}")
            }
        } catch (e: Exception) {
            Log.e("MarketplaceRepo", "Network exception syncing marketplace", e)
        }
    }

    override suspend fun placeBid(offerId: String, msisdn: String): Flow<Boolean> = flow {
        try {
            kotlinx.coroutines.delay(1500) // Simulate network call
            
            offerDao.updateOfferStatus(offerId, "accepted")
            emit(true)
        } catch (e: Exception) {
            Log.e("MarketplaceRepo", "Error placing bid", e)
            emit(false)
        }
    }

    override suspend fun getMarketPrices(crop: String, region: String): MarketPrices {
        val response = api.getMarketPrices(crop, region)
        if (response.isSuccessful) {
            val body = response.body() ?: throw Exception("Empty response body")
            return MarketPrices(
                crop = body.crop,
                region = body.region,
                unit = body.unit,
                today = PriceSeriesPoint(body.today.date, body.today.ugx),
                last7Min = body.last7_min,
                last7Max = body.last7_max,
                last7Avg = body.last7_avg,
                trend = body.trend,
                series = body.series.map { PriceSeriesPoint(it.date, it.ugx) }
            )
        } else {
            throw Exception("Failed to fetch market prices: ${response.message()}")
        }
    }
}
