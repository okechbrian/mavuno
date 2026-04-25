package com.mavuno.data.local

import com.mavuno.data.local.dao.*
import com.mavuno.data.local.entity.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import javax.inject.Inject

class DatabaseSeeder @Inject constructor(
    private val farmerDao: FarmerDao,
    private val buyerDao: BuyerDao,
    private val hardwarePingDao: HardwarePingDao,
    private val ectBalanceDao: EctBalanceDao,
    private val offerDao: OfferDao
) {
    suspend fun seedIfNeeded() = withContext(Dispatchers.IO) {
        // Seed Farmers
        val demoFarmer = FarmerEntity(
            farmId = "UG-MBL-0001",
            name = "John Doe",
            region = "Mbale",
            phoneNumber = "+256700000001",
            mainCrop = "Coffee",
            ypsScore = 85
        )
        farmerDao.insertFarmers(listOf(demoFarmer))

        // Seed Balance
        ectBalanceDao.insertBalance(
            EctBalanceEntity(
                farmId = "UG-MBL-0001",
                balance = 150.75,
                lastUpdated = System.currentTimeMillis()
            )
        )

        // Seed Pings
        hardwarePingDao.insertPing(
            HardwarePingEntity(
                id = "P-001",
                farmId = "UG-MBL-0001",
                timestamp = System.currentTimeMillis(),
                soilMoisture = 28.5,
                soilTemperature = 22.1,
                nitrogen = 22.0,
                phosphorus = 14.5,
                potassium = 12.0,
                ambientHumidity = 65.0,
                rainfall = 1.2,
                signature = "MOCKED_SIG",
                isSynced = true
            )
        )

        // Seed Buyers
        val demoBuyer = BuyerEntity(
            buyerId = "BUYER-MBL-001",
            name = "Mbale Coffee SACCO",
            region = "Mbale",
            phoneNumber = "+256700111222",
            cropsPurchased = listOf("Coffee", "Maize"),
            floorPrice = 3500.0
        )
        buyerDao.insertBuyers(listOf(demoBuyer))

        // Seed Offers
        offerDao.insertOffers(listOf(
            OfferEntity(
                id = "OF-DEMO-001",
                farmId = "UG-MBL-0001",
                farmerName = "John Doe",
                crop = "Coffee",
                quantityKg = 500,
                floorPriceUgx = 4200,
                region = "Mbale",
                status = "open",
                createdAt = System.currentTimeMillis(),
                paymentStatus = "none"
            )
        ))
    }
}
