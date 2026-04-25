package com.mavuno.features.farmer

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mavuno.domain.model.EctBalance
import com.mavuno.domain.model.Farmer
import com.mavuno.domain.repository.EctBalanceRepository
import com.mavuno.domain.repository.FarmerRepository
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
    val error: String? = null
)

@HiltViewModel
class FarmerDashboardViewModel @Inject constructor(
    private val farmerRepository: FarmerRepository,
    private val ectBalanceRepository: EctBalanceRepository
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
                FarmerDashboardUiState(
                    isLoading = false,
                    farmer = farmer,
                    ectBalance = balance
                )
            }.collect { state ->
                _uiState.value = state
            }
        }
    }
}
