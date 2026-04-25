package com.mavuno.domain.model

data class Farmer(
    val farmId: String,
    val name: String,
    val region: String,
    val phoneNumber: String,
    val mainCrop: String,
    val ypsScore: Int
)
