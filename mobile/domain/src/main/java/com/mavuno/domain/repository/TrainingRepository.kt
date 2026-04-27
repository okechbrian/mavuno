package com.mavuno.domain.repository

import com.mavuno.domain.model.TrainingModule
import kotlinx.coroutines.flow.Flow

interface TrainingRepository {
    fun getTrainingModules(): Flow<List<TrainingModule>>
    fun markModuleCompleted(moduleId: String): Flow<Boolean>
    fun getModuleById(moduleId: String): Flow<TrainingModule?>
}
