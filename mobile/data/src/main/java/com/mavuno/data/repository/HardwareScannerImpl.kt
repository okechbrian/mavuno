package com.mavuno.data.repository

import com.mavuno.domain.model.HardwarePing
import com.mavuno.domain.model.HardwareScanResult
import com.mavuno.domain.repository.HardwareScanner
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import java.util.*
import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec
import javax.inject.Inject

class HardwareScannerImpl @Inject constructor() : HardwareScanner {

    private val _devices = MutableStateFlow<List<HardwareScanResult>>(emptyList())

    override fun startBluetoothScan(): Flow<List<HardwareScanResult>> {
        // Prototype: Simulated Bluetooth LE scan discovering Mavuno IoT Nodes
        _devices.value = listOf(
            HardwareScanResult("MAVUNO-NODE-01", "00:1A:7D:DA:71:11", -45),
            HardwareScanResult("MAVUNO-NODE-02", "00:1A:7D:DA:71:12", -60),
            HardwareScanResult("UNKNOWN-BLE", "11:22:33:44:55:66", -90)
        )
        return _devices.asStateFlow()
    }

    override fun stopBluetoothScan() {
        _devices.value = emptyList()
    }

    override suspend fun connectAndPing(macAddress: String, farmId: String): HardwarePing {
        delay(1500) // Simulating BLE handshake and telemetry fetch
        return generateMockPing(farmId)
    }

    override suspend fun fallbackCameraPing(qrCodeData: String, farmId: String): HardwarePing {
        delay(500) // Simulating QR data processing and node verification
        return generateMockPing(farmId)
    }

    private fun generateMockPing(farmId: String): HardwarePing {
        val timestamp = System.currentTimeMillis()
        val random = Random()
        // Generate realistic agronomic data
        val soilMoisture = 30.0 + random.nextDouble() * 20
        val soilTemp = 22.0 + random.nextDouble() * 8
        val n = 20.0 + random.nextDouble() * 5
        val p = 15.0 + random.nextDouble() * 5
        val k = 10.0 + random.nextDouble() * 5
        val humidity = 50.0 + random.nextDouble() * 30
        val rainfall = random.nextDouble() * 5

        // The exact serialization payload required by the Mavuno Protocol ledger
        val telemetry = "$farmId|$timestamp|$soilMoisture|$soilTemp|$n|$p|$k|$humidity|$rainfall"
        
        // In a production environment, this signing happens ON THE HARDWARE SECURE ENCLAVE.
        // For the prototype, we simulate the hardware generating the HMAC-SHA256 signature.
        val hardwareSecret = "MAVUNO_HARDWARE_KEY_2026"
        val signature = signTelemetry(telemetry, hardwareSecret)

        return HardwarePing(
            id = UUID.randomUUID().toString(),
            farmId = farmId,
            timestamp = timestamp,
            soilMoisture = soilMoisture,
            soilTemperature = soilTemp,
            nitrogen = n,
            phosphorus = p,
            potassium = k,
            ambientHumidity = humidity,
            rainfall = rainfall,
            signature = signature
        )
    }

    private fun signTelemetry(data: String, secret: String): String {
        return try {
            val sha256Hmac = Mac.getInstance("HmacSHA256")
            val secretKey = SecretKeySpec(secret.toByteArray(), "HmacSHA256")
            sha256Hmac.init(secretKey)
            
            val signedBytes = sha256Hmac.doFinal(data.toByteArray())
            android.util.Base64.encodeToString(signedBytes, android.util.Base64.NO_WRAP)
        } catch (e: Exception) {
            "SIGNATURE_ERROR"
        }
    }
}
