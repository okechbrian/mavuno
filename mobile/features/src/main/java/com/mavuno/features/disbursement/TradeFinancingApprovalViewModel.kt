package com.mavuno.features.disbursement

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mavuno.domain.model.Farmer
import com.mavuno.domain.model.YieldPriority
import com.mavuno.domain.repository.FarmerRepository
import com.mavuno.domain.repository.YieldPriorityRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.util.*
import javax.inject.Inject
import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec

data class DisbursementUiState(
    val isLoading: Boolean = false,
    val farmer: Farmer? = null,
    val isSuccess: Boolean = false,
    val error: String? = null
)

@HiltViewModel
class TradeFinancingApprovalViewModel @Inject constructor(
    private val farmerRepository: FarmerRepository,
    private val yieldPriorityRepository: YieldPriorityRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(DisbursementUiState())
    val uiState: StateFlow<DisbursementUiState> = _uiState.asStateFlow()

    fun loadFarmer(farmId: String) {
        viewModelScope.launch {
            farmerRepository.getFarmerById(farmId).collect { farmer ->
                _uiState.value = _uiState.value.copy(farmer = farmer)
            }
        }
    }

    fun approveFinancing(farmId: String, yps: Int, kg: Int, aggregationPoint: String) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true)
            try {
                val timestamp = System.currentTimeMillis()
                val expiresAt = timestamp + (30L * 24 * 60 * 60 * 1000) // 30 days
                val id = "YP-" + UUID.randomUUID().toString().take(8).uppercase()
                
                // Cryptographic signature for the offline aggregation point
                val payload = "$farmId|$yps|$kg|$aggregationPoint|$expiresAt"
                val signature = signPayload(payload, "MAVUNO_OFFLINE_SECRET_2026")

                val yieldPriority = YieldPriority(
                    id = id,
                    farmId = farmId,
                    yps = yps,
                    kgAllocated = kg,
                    kgRemaining = kg,
                    aggregationPoint = aggregationPoint,
                    status = "active",
                    createdAt = timestamp,
                    expiresAt = expiresAt,
                    signature = signature
                )

                yieldPriorityRepository.saveYieldPriorityLocally(yieldPriority)
                _uiState.value = _uiState.value.copy(isLoading = false, isSuccess = true)
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(isLoading = false, error = e.message)
            }
        }
    }

    private fun signPayload(data: String, secret: String): String {
        return try {
            val sha256Hmac = Mac.getInstance("HmacSHA256")
            val secretKey = SecretKeySpec(secret.toByteArray(), "HmacSHA256")
            sha256Hmac.init(secretKey)
            val signedBytes = sha256Hmac.doFinal(data.toByteArray())
            android.util.Base64.encodeToString(signedBytes, android.util.Base64.NO_WRAP)
        } catch (e: Exception) {
            "PAYLOAD_SIG_ERR"
        }
    }
}
