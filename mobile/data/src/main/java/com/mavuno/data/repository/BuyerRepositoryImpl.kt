package com.mavuno.data.repository

import com.mavuno.data.local.dao.BuyerDao
import com.mavuno.data.local.entity.toDomain
import com.mavuno.domain.model.Buyer
import com.mavuno.domain.repository.BuyerRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject

class BuyerRepositoryImpl @Inject constructor(
    private val dao: BuyerDao
) : BuyerRepository {
    override fun getAllBuyers(): Flow<List<Buyer>> {
        return dao.getAllBuyers().map { entities ->
            entities.map { it.toDomain() }
        }
    }

    override suspend fun syncBuyers() {
        // TODO: Implement remote API call and save to Room
    }
}
