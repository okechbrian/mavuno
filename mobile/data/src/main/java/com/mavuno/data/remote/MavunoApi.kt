package com.mavuno.data.remote

import com.mavuno.data.remote.model.*
import com.mavuno.domain.model.Offer
import retrofit2.Response
import retrofit2.http.*

interface MavunoApi {

    @POST("login")
    suspend fun login(@Body request: LoginRequest): Response<LoginResponse>

    @GET("score/{farmId}")
    suspend fun getScore(@Path("farmId") farmId: String): Response<ScoreResponse>

    @GET("ect/balance/{farmId}")
    suspend fun getEctBalance(@Path("farmId") farmId: String): Response<EctBalanceResponse>

    @POST("sensor/telemetry")
    suspend fun sendTelemetry(@Body request: TelemetryRequest): Response<Unit>

    @GET("crp/offers")
    suspend fun getOffers(): Response<Map<String, List<Offer>>>
}
