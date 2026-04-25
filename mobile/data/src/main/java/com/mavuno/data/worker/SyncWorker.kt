package com.mavuno.data.worker

import android.content.Context
import androidx.hilt.work.HiltWorker
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.mavuno.domain.repository.HardwarePingRepository
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject

// Note: To use Hilt with WorkManager we also need androidx.hilt:hilt-work
@HiltWorker
class SyncWorker @AssistedInject constructor(
    @Assisted context: Context,
    @Assisted workerParams: WorkerParameters,
    private val hardwarePingRepository: HardwarePingRepository
) : CoroutineWorker(context, workerParams) {

    override suspend fun doWork(): Result {
        return try {
            // Attempt to sync offline telemetry data
            hardwarePingRepository.syncUnsyncedPings()
            Result.success()
        } catch (e: Exception) {
            Result.retry()
        }
    }
}
