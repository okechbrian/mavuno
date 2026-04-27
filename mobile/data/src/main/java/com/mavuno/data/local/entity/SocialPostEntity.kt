package com.mavuno.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey
import com.mavuno.domain.model.SocialPost

@Entity(tableName = "social_posts")
data class SocialPostEntity(
    @PrimaryKey val id: String,
    val farmId: String,
    val farmerName: String,
    val district: String,
    val crop: String,
    val body: String,
    val photoUrl: String?,
    val isVerified: Boolean,
    val yps: Int?,
    val createdAt: Long,
    val reactionsJson: String // Serialized Map<String, Int>
) {
    fun toDomain(): SocialPost {
        // Simple manual parsing or use Gson/Moshi if available
        // For prototype we'll assume it's handled by Converters or similar
        return SocialPost(
            id = id,
            farmId = farmId,
            farmerName = farmerName,
            district = district,
            crop = crop,
            body = body,
            photoUrl = photoUrl,
            isVerified = isVerified,
            yps = yps,
            createdAt = createdAt,
            reactions = emptyMap() // Placeholder
        )
    }
}
