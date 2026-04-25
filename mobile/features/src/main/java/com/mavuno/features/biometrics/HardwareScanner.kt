package com.mavuno.features.biometrics

import com.mavuno.domain.model.HardwarePing
import kotlinx.coroutines.delay
import java.util.*
import javax.inject.Inject
import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec
import java.security.NoSuchAlgorithmException

class HardwareScanner @Inject constructor() {

    /**
     * Simulates scanning for a soil sensor via Bluetooth and receiving a telemetry packet.
     * In a real app, this would use Android's BluetoothLeScanner.
     */
    suspend fun scanSoilSensor(farmId: String): HardwarePing {
        // Simulate scanning delay
        delay(2000)

        val timestamp = System.currentTimeMillis()
        val random = Random()

        // Mock telemetry data
        val soilMoisture = 35.0 + random.nextDouble() * 10
        val soilTemp = 24.0 + random.nextDouble() * 5
        val n = 20.0 + random.nextDouble() * 5
        val p = 15.0 + random.nextDouble() * 5
        val k = 10.0 + random.nextDouble() * 5
        val humidity = 60.0 + random.nextDouble() * 10
        val rainfall = 2.0 + random.nextDouble() * 2

        // Create telemetry string for signing (matching the logic in offline_pump_demo.py)
        val telemetry = "$farmId|$timestamp|$soilMoisture|$soilTemp|$n|$p|$k|$humidity|$rainfall"
        
        // Mock a hardware secret key (in production this is stored in secure hardware)
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
            // Base64 encoding the signature
            android.util.Base64.encodeToString(signedBytes, android.util.Base64.NO_WRAP)
        } catch (e: Exception) {
            "SIGNATURE_ERROR"
        }
    }
}
