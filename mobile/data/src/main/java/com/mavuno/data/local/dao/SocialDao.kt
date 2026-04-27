package com.mavuno.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.mavuno.data.local.entity.SocialPostEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface SocialDao {
    @Query("SELECT * FROM social_posts ORDER BY createdAt DESC")
    fun getFeed(): Flow<List<SocialPostEntity>>

    @Query("SELECT * FROM social_posts WHERE district = :district ORDER BY createdAt DESC")
    fun getFeedByDistrict(district: String): Flow<List<SocialPostEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertPosts(posts: List<SocialPostEntity>)

    @Query("DELETE FROM social_posts")
    suspend fun clearFeed()
}
