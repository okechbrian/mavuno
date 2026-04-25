package com.mavuno.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey
import com.mavuno.domain.model.HardwarePing

@Entity(tableName = "hardware_pings")
data class HardwarePingEntity(
    @PrimaryKey val id: String,
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
    val isSynced: Boolean
)

fun HardwarePingEntity.toDomain() = HardwarePing(
    id = id,
    farmId = farmId,
    timestamp = timestamp,
    soilMoisture = soilMoisture,
    soilTemperature = soilTemperature,
    nitrogen = nitrogen,
    phosphorus = phosphorus,
    potassium = potassium,
    ambientHumidity = ambientHumidity,
    rainfall = rainfall,
    signature = signature,
    isSynced = isSynced
)

fun HardwarePing.toEntity() = HardwarePingEntity(
    id = id,
    farmId = farmId,
    timestamp = timestamp,
    soilMoisture = soilMoisture,
    soilTemperature = soilTemperature,
    nitrogen = nitrogen,
    phosphorus = phosphorus,
    potassium = potassium,
    ambientHumidity = ambientHumidity,
    rainfall = rainfall,
    signature = signature,
    isSynced = isSynced
)
