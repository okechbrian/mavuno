package com.mavuno.domain.model

data class TrainingModule(
    val id: String,
    val title: String,
    val description: String,
    val durationMinutes: Int,
    val thumbnailUrl: String,
    val isCompleted: Boolean,
    val progress: Float // 0.0 to 1.0
)
