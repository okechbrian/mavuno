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

    @GET("feed")
    suspend fun getFeed(@Query("district") district: String? = null): Response<FeedResponse>

    @POST("feed")
    suspend fun createPost(@Body request: PostCreateRequest): Response<PostResponse>

    @POST("crp/ask")
    suspend fun askAdvisor(@Body request: AskRequest): Response<AskResponse>

    @GET("crp/prices")
    suspend fun getMarketPrices(
        @Query("crop") crop: String,
        @Query("region") region: String
    ): Response<MarketPricesResponse>

    @GET("training/modules")
    suspend fun getTrainingModules(): Response<TrainingModulesResponse>

    @POST("training/complete")
    suspend fun completeModule(@Body request: Map<String, String>): Response<Unit>

    @GET("farmer/{farmId}/certifications")
    suspend fun getCertifications(@Path("farmId") farmId: String): Response<CertificationsResponse>

    @POST("payments/batch")
    suspend fun initiateBatchPayment(@Body request: BatchPaymentRequest): Response<BatchPaymentResponse>

    @GET("farms")
    suspend fun getFarms(): Response<Map<String, FarmDto>>

    @POST("farms/onboard")
    suspend fun onboardFarm(@Body request: OnboardRequest): Response<OnboardResponse>
}
