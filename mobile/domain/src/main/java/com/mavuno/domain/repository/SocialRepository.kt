package com.mavuno.domain.repository

import com.mavuno.domain.model.SocialPost
import kotlinx.coroutines.flow.Flow

interface SocialRepository {
    fun getFeed(district: String? = null): Flow<List<SocialPost>>
    suspend fun syncFeed(district: String? = null)
    suspend fun createPost(body: String, photoUrl: String? = null, isVerified: Boolean = false)
    suspend fun reactToPost(postId: String, emoji: String)
    suspend fun askAdvisor(farmId: String, question: String, makePublic: Boolean): String
}
