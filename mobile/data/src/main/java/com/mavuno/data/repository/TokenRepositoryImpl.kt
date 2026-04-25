package com.mavuno.data.repository

import com.mavuno.data.local.dao.TokenDao
import com.mavuno.data.local.entity.toDomain
import com.mavuno.data.local.entity.toEntity
import com.mavuno.domain.model.Token
import com.mavuno.domain.repository.TokenRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject

class TokenRepositoryImpl @Inject constructor(
    private val dao: TokenDao
) : TokenRepository {
    override fun getTokensForFarm(farmId: String): Flow<List<Token>> {
        return dao.getTokensForFarm(farmId).map { entities ->
            entities.map { it.toDomain() }
        }
    }

    override suspend fun saveTokenLocally(token: Token) {
        dao.insertToken(token.toEntity())
    }

    override suspend fun syncTokens() {
        // TODO: Sync newly created tokens to the global ledger
    }
}
