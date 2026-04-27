package com.mavuno.features.farmer

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mavuno.data.remote.MavunoApi
import com.mavuno.data.remote.model.AskRequest
import com.mavuno.data.remote.model.TelemetryRequest
import com.mavuno.domain.model.EctBalance
import com.mavuno.domain.model.Farmer
import com.mavuno.domain.model.MarketPrices
import com.mavuno.domain.repository.EctBalanceRepository
import com.mavuno.domain.repository.FarmerRepository
import com.mavuno.domain.repository.MarketplaceRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.launch
import javax.inject.Inject

data class FarmerDashboardUiState(
    val isLoading: Boolean = true,
    val farmer: Farmer? = null,
    val ectBalance: EctBalance? = null,
    val marketPrices: MarketPrices? = null,
    val activeOffersCount: Int = 2,
    val totalHarvestsCount: Int = 14,
    val error: String? = null,
    val aiAnswer: String? = null
)

@HiltViewModel
class FarmerDashboardViewModel @Inject constructor(
    private val farmerRepository: FarmerRepository,
    private val ectBalanceRepository: EctBalanceRepository,
    private val marketplaceRepository: MarketplaceRepository,
    private val api: MavunoApi
) : ViewModel() {

    private val _uiState = MutableStateFlow(FarmerDashboardUiState())
    val uiState: StateFlow<FarmerDashboardUiState> = _uiState.asStateFlow()

    fun loadDashboard(farmId: String) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true)
            
            combine(
                farmerRepository.getFarmerById(farmId),
                ectBalanceRepository.getBalanceForFarm(farmId)
            ) { farmer, balance ->
                var mktPrices: MarketPrices? = null
                if (farmer != null) {
                    try {
                        mktPrices = marketplaceRepository.getMarketPrices(farmer.mainCrop, farmer.region)
                    } catch (e: Exception) {
                        // ignore error for market prices on dashboard
                    }
                }
                
                _uiState.value.copy(
                    isLoading = false,
                    farmer = farmer,
                    ectBalance = balance,
                    marketPrices = mktPrices
                )
            }.collect { state ->
                _uiState.value = state
            }
        }
    }

    fun pingSensor(farmId: String) {
        viewModelScope.launch {
            try {
                val req = TelemetryRequest(
                    farm_id = farmId,
                    soil_moisture = 15.0 + Math.random() * 10,
                    temp_c = 28.0 + Math.random() * 6,
                    rainfall_mm = Math.random() * 2,
                    humidity_pct = 40.0 + Math.random() * 20,
                    n_mg_kg = 20.0 + Math.random() * 20,
                    p_mg_kg = 10.0 + Math.random() * 10,
                    k_mg_kg = 150.0 + Math.random() * 100
                )
                api.sendTelemetry(req)
                loadDashboard(farmId)
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(error = "Ping failed: ${e.message}")
            }
        }
    }

    fun askAdvisor(farmId: String, question: String) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(aiAnswer = "Thinking...")
            try {
                val res = api.askAdvisor(AskRequest(farmId, question, false))
                if (res.isSuccessful) {
                    _uiState.value = _uiState.value.copy(aiAnswer = res.body()?.answer ?: "No answer provided.")
                } else {
                    _uiState.value = _uiState.value.copy(aiAnswer = "Error connecting to AI Advisor.")
                }
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(aiAnswer = "Network error: ${e.message}")
            }
        }
    }

    fun clearAiAnswer() {
        _uiState.value = _uiState.value.copy(aiAnswer = null)
    }
}
