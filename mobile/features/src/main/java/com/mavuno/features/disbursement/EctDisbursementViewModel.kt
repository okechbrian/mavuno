package com.mavuno.features.disbursement

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mavuno.domain.model.Farmer
import com.mavuno.domain.model.Token
import com.mavuno.domain.repository.FarmerRepository
import com.mavuno.domain.repository.TokenRepository
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
class EctDisbursementViewModel @Inject constructor(
    private val farmerRepository: FarmerRepository,
    private val tokenRepository: TokenRepository
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

    fun disburseEct(farmId: String, yps: Int, kwh: Int, pumpNode: String) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true)
            try {
                val timestamp = System.currentTimeMillis()
                val expiresAt = timestamp + (30L * 24 * 60 * 60 * 1000) // 30 days
                val tokenId = "TK-" + UUID.randomUUID().toString().take(8).uppercase()
                
                // Cryptographic signature for the offline pump
                val payload = "$farmId|$yps|$kwh|$pumpNode|$expiresAt"
                val signature = signToken(payload, "MAVUNO_OFFLINE_SECRET_2026")

                val token = Token(
                    id = tokenId,
                    farmId = farmId,
                    yps = yps,
                    kwhAllocated = kwh,
                    kwhRemaining = kwh,
                    pumpNode = pumpNode,
                    status = "active",
                    createdAt = timestamp,
                    expiresAt = expiresAt,
                    signature = signature
                )

                tokenRepository.saveTokenLocally(token)
                _uiState.value = _uiState.value.copy(isLoading = false, isSuccess = true)
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(isLoading = false, error = e.message)
            }
        }
    }

    private fun signToken(data: String, secret: String): String {
        return try {
            val sha256Hmac = Mac.getInstance("HmacSHA256")
            val secretKey = SecretKeySpec(secret.toByteArray(), "HmacSHA256")
            sha256Hmac.init(secretKey)
            val signedBytes = sha256Hmac.doFinal(data.toByteArray())
            android.util.Base64.encodeToString(signedBytes, android.util.Base64.NO_WRAP)
        } catch (e: Exception) {
            "TOKEN_SIG_ERR"
        }
    }
}
