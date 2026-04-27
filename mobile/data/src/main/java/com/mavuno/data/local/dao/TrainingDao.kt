package com.mavuno.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.mavuno.data.local.entity.TrainingModuleEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface TrainingDao {
    @Query("SELECT * FROM training_modules")
    fun observeModules(): Flow<List<TrainingModuleEntity>>

    @Query("SELECT * FROM training_modules WHERE id = :id LIMIT 1")
    fun observeModuleById(id: String): Flow<TrainingModuleEntity?>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertModules(modules: List<TrainingModuleEntity>)

    @Query("UPDATE training_modules SET isCompleted = 1, progress = 1.0 WHERE id = :id")
    suspend fun markModuleCompleted(id: String)
}
