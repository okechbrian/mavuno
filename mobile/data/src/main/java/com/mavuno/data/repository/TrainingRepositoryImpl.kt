package com.mavuno.data.repository

import android.util.Log
import com.mavuno.data.local.dao.TrainingDao
import com.mavuno.data.local.entity.TrainingModuleEntity
import com.mavuno.data.remote.MavunoApi
import com.mavuno.domain.model.TrainingModule
import com.mavuno.domain.repository.TrainingRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.emitAll
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.onStart
import javax.inject.Inject

class TrainingRepositoryImpl @Inject constructor(
    private val api: MavunoApi,
    private val trainingDao: TrainingDao
) : TrainingRepository {

    override fun getTrainingModules(): Flow<List<TrainingModule>> = flow {
        // Offline-first: Emit local data first, then refresh from network
        emitAll(
            trainingDao.observeModules().map { entities ->
                entities.map { it.toDomain() }
            }.onStart {
                try {
                    val response = api.getTrainingModules()
                    if (response.isSuccessful) {
                        response.body()?.modules?.let { dtos ->
                            val newEntities = dtos.map {
                                TrainingModuleEntity(
                                    id = it.id,
                                    title = it.title,
                                    description = it.description,
                                    durationMinutes = it.duration_minutes ?: 30, // Safely mapped from DTO
                                    thumbnailUrl = it.content_url ?: "https://images.unsplash.com/photo-1595855761858-a4005d53f5d5?q=80&w=800&auto=format&fit=crop",
                                    isCompleted = false,
                                    progress = 0.0f
                                )
                            }
                            trainingDao.insertModules(newEntities)
                        }
                    } else {
                        Log.e("TrainingRepo", "API Error: ${response.code()} - ${response.message()}")
                    }
                } catch (e: Exception) {
                    Log.e("TrainingRepo", "Network exception syncing modules", e)
                    // Network error, ignore and continue observing local cache
                }
            }
        )
    }

    override fun markModuleCompleted(moduleId: String): Flow<Boolean> = flow {
        try {
            // Update remote API
            val response = api.completeModule(mapOf("module_id" to moduleId))
            if (response.isSuccessful) {
                // Update local database
                trainingDao.markModuleCompleted(moduleId)
                emit(true)
            } else {
                Log.e("TrainingRepo", "API Error marking complete: ${response.code()}")
                emit(false)
            }
        } catch (e: Exception) {
            Log.e("TrainingRepo", "Network exception marking complete", e)
            emit(false)
        }
    }

    override fun getModuleById(moduleId: String): Flow<TrainingModule?> {
        return trainingDao.observeModuleById(moduleId).map { it?.toDomain() }
    }
}
