package com.mavuno.domain.repository

import com.mavuno.domain.model.HardwarePing
import com.mavuno.domain.model.HardwareScanResult
import kotlinx.coroutines.flow.Flow

interface HardwareScanner {
    fun startBluetoothScan(): Flow<List<HardwareScanResult>>
    fun stopBluetoothScan()
    suspend fun connectAndPing(macAddress: String, farmId: String): HardwarePing
    suspend fun fallbackCameraPing(qrCodeData: String, farmId: String): HardwarePing
}
