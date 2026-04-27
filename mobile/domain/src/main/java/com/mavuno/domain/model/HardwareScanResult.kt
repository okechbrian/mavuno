package com.mavuno.domain.model

data class HardwareScanResult(
    val deviceName: String,
    val macAddress: String,
    val rssi: Int,
    val isConnected: Boolean = false
)
