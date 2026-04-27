package com.mavuno.data.repository

import com.mavuno.data.local.dao.SocialDao
import com.mavuno.data.local.entity.SocialPostEntity
import com.mavuno.data.remote.MavunoApi
import com.mavuno.data.remote.model.AskRequest
import com.mavuno.data.remote.model.PostCreateRequest
import com.mavuno.domain.model.SocialPost
import com.mavuno.domain.repository.SocialRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject

class SocialRepositoryImpl @Inject constructor(
    private val api: MavunoApi,
    private val socialDao: SocialDao
) : SocialRepository {

    override fun getFeed(district: String?): Flow<List<SocialPost>> {
        val flow = if (district != null) {
            socialDao.getFeedByDistrict(district)
        } else {
            socialDao.getFeed()
        }
        return flow.map { entities -> entities.map { it.toDomain() } }
    }

    override suspend fun syncFeed(district: String?) {
        try {
            val response = api.getFeed(district)
            if (response.isSuccessful) {
                response.body()?.posts?.let { posts ->
                    val entities = posts.map { post ->
                        SocialPostEntity(
                            id = post.id,
                            farmId = post.farm_id,
                            farmerName = post.farmer_name,
                            district = post.district,
                            crop = post.crop,
                            body = post.body,
                            photoUrl = post.photo_url,
                            isVerified = post.is_verified == 1,
                            yps = post.yps,
                            createdAt = post.created_at,
                            reactionsJson = "" // TODO: Serialize reactions
                        )
                    }
                    socialDao.insertPosts(entities)
                }
            }
        } catch (e: Exception) {
            // Handle network error
        }
    }

    override suspend fun createPost(body: String, photoUrl: String?, isVerified: Boolean) {
        val request = PostCreateRequest(body, photoUrl, isVerified)
        api.createPost(request)
        syncFeed() // Refresh feed after posting
    }

    override suspend fun reactToPost(postId: String, emoji: String) {
        // api.reactToPost(postId, emoji) // TODO: Implement in API
    }

    override suspend fun askAdvisor(farmId: String, question: String, makePublic: Boolean): String {
        val response = api.askAdvisor(AskRequest(farmId, question, makePublic))
        return if (response.isSuccessful) {
            response.body()?.answer ?: "No answer received"
        } else {
            "Error contacting advisor"
        }
    }
}
