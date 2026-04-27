package com.mavuno.domain.model

data class PriceSeriesPoint(
    val date: String,
    val ugx: Int
)

data class MarketPrices(
    val crop: String,
    val region: String,
    val unit: String,
    val today: PriceSeriesPoint,
    val last7Min: Int,
    val last7Max: Int,
    val last7Avg: Int,
    val trend: String,
    val series: List<PriceSeriesPoint>
)
