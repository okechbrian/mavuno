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

data class PostResponse(
    val id: String,
    val farm_id: String,
    val farmer_name: String,
    val district: String,
    val crop: String,
    val body: String,
    val photo_url: String?,
    val is_verified: Int,
    val yps: Int?,
    val created_at: Long,
    val reactions: Map<String, Int>
)

data class FeedResponse(
    val posts: List<PostResponse>
)

data class PostCreateRequest(
    val body: String,
    val photo_url: String? = null,
    val is_verified: Boolean = false
)

data class AskRequest(
    val farm_id: String,
    val question: String,
    val make_public: Boolean = false
)

data class AskResponse(
    val farm_id: String,
    val answer: String,
    val source: String,
    val context: Map<String, Any>
)

data class PriceSeriesPoint(
    val date: String,
    val ugx: Int
)

data class MarketPricesResponse(
    val crop: String,
    val region: String,
    val unit: String,
    val today: PriceSeriesPoint,
    val last7_min: Int,
    val last7_max: Int,
    val last7_avg: Int,
    val trend: String,
    val series: List<PriceSeriesPoint>
)

data class TrainingModuleResponse(
    val id: String,
    val title: String,
    val description: String,
    val category: String,
    val xp_reward: Int,
    val content_url: String?,
    val duration_minutes: Int?
)

data class TrainingModulesResponse(
    val modules: List<TrainingModuleResponse>
)

data class CertificationResponse(
    val id: String,
    val farm_id: String,
    val module_id: String,
    val issued_at: Long,
    val ledger_hash: String,
    val title: String,
    val category: String,
    val xp_reward: Int
)

data class CertificationsResponse(
    val certifications: List<CertificationResponse>
)

data class OnboardRequest(
    val name: String,
    val district: String,
    val crop: String,
    val phone: String,
    val acres: Double
)

data class OnboardResponse(
    val ok: Boolean,
    val farm_id: String
)

data class FarmDto(
    val farmer_name: String,
    val district: String,
    val crop: String,
    val phone: String,
    val acres: Double
)


data class BatchPaymentRequest(
    val offer_ids: List<String>,
    val msisdn: String
)

data class BatchPaymentResponse(
    val ok: Boolean,
    val batch_id: String,
    val total_ugx: Int,
    val payment_ids: List<String>
)
