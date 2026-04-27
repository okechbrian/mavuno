package com.mavuno.data.repository

import com.mavuno.data.local.dao.BuyerDao
import com.mavuno.data.local.entity.BatchPaymentEntity
import com.mavuno.data.local.entity.BuyerProfileEntity
import com.mavuno.data.local.entity.toEntity
import com.mavuno.data.remote.MavunoApi
import com.mavuno.domain.model.BatchPayment
import com.mavuno.domain.model.BuyerProfile
import com.mavuno.domain.repository.BuyerRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject

class BuyerRepositoryImpl @Inject constructor(
    private val buyerDao: BuyerDao,
    private val api: MavunoApi
) : BuyerRepository {

    override fun getBuyerProfile(buyerId: String): Flow<BuyerProfile?> {
        return buyerDao.observeProfile(buyerId).map { it?.toDomain() }
    }

    override fun getBatchPayments(buyerId: String): Flow<List<BatchPayment>> {
        return buyerDao.observeBatchPayments(buyerId).map { entities ->
            entities.map { it.toDomain() }
        }
    }

    override suspend fun syncBuyerData(buyerId: String) {
        try {
            // Mocking sync since there's no explicit endpoint for full profile/history yet
            // In a real app, you'd fetch from api.getBuyerProfile(buyerId)
            
            val mockProfile = BuyerProfile(
                id = buyerId,
                name = "Mukisa Sourcing Hub",
                company = "Mukisa Sustainable Farms",
                region = "Central Uganda",
                isVerified = true,
                totalVolumeKg = 4500,
                activeContracts = 3,
                ectSpent = 125.5
            )
            buyerDao.insertProfile(mockProfile.toEntity())

            val mockPayments = listOf(
                BatchPayment("BP-001", System.currentTimeMillis() - 86400000, 1500000, 5, "Settled", listOf("P1", "P2")),
                BatchPayment("BP-002", System.currentTimeMillis() - 172800000, 2400000, 8, "Pending", listOf("P3", "P4")),
                BatchPayment("BP-003", System.currentTimeMillis() - 259200000, 900000, 2, "Failed", listOf("P5"))
            )
            buyerDao.insertBatchPayments(mockPayments.map { it.toEntity(buyerId) })

        } catch (e: Exception) {
            // Handle error
        }
    }
}
