package com.mavuno.data.remote.model

data class LoginRequest(
    val role: String,
    val id_or_phone: String,
    val pin_or_password: String
)

data class LoginResponse(
    val ok: Boolean,
    val redirect: String?,
    val error: String?
)

data class TelemetryRequest(
    val farm_id: String,
    val soil_moisture: Double,
    val temp_c: Double,
    val rainfall_mm: Double,
    val humidity_pct: Double,
    val n_mg_kg: Double,
    val p_mg_kg: Double,
    val k_mg_kg: Double
)

data class ScoreResponse(
    val farm_id: String,
    val yps: Int,
    val credit_health: String,
    val kwh_allocated: Int,
    val credit_ceiling_ugx: Int,
    val diagnostics: List<String>
)

data class EctBalanceResponse(
    val farm_id: String,
    val balance: Double
)
