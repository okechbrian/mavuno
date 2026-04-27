package com.mavuno.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey
import com.mavuno.domain.model.TrainingModule

@Entity(tableName = "training_modules")
data class TrainingModuleEntity(
    @PrimaryKey val id: String,
    val title: String,
    val description: String,
    val durationMinutes: Int,
    val thumbnailUrl: String,
    val isCompleted: Boolean,
    val progress: Float
) {
    fun toDomain() = TrainingModule(
        id = id,
        title = title,
        description = description,
        durationMinutes = durationMinutes,
        thumbnailUrl = thumbnailUrl,
        isCompleted = isCompleted,
        progress = progress
    )
}

fun TrainingModule.toEntity() = TrainingModuleEntity(
    id = id,
    title = title,
    description = description,
    durationMinutes = durationMinutes,
    thumbnailUrl = thumbnailUrl,
    isCompleted = isCompleted,
    progress = progress
)
