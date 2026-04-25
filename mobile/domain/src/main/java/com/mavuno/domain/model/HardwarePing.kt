package com.mavuno.domain.model

data class HardwarePing(
    val id: String,
    val farmId: String,
    val timestamp: Long,
    val soilMoisture: Double,
    val soilTemperature: Double,
    val nitrogen: Double,
    val phosphorus: Double,
    val potassium: Double,
    val ambientHumidity: Double,
    val rainfall: Double,
    val signature: String,
    val isSynced: Boolean = false
)
