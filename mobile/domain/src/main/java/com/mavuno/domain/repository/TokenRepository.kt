package com.mavuno.domain.repository

import com.mavuno.domain.model.Token
import kotlinx.coroutines.flow.Flow

interface TokenRepository {
    fun getTokensForFarm(farmId: String): Flow<List<Token>>
    suspend fun saveTokenLocally(token: Token)
    suspend fun syncTokens()
}
