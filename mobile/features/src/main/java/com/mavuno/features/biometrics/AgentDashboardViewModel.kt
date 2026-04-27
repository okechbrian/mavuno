package com.mavuno.features.biometrics

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mavuno.data.remote.MavunoApi
import com.mavuno.data.remote.model.FarmDto
import com.mavuno.data.remote.model.OnboardRequest
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class AgentDashboardUiState(
    val isLoading: Boolean = true,
    val farms: Map<String, FarmDto> = emptyMap(),
    val error: String? = null
)

@HiltViewModel
class AgentDashboardViewModel @Inject constructor(
    private val api: MavunoApi
) : ViewModel() {

    private val _uiState = MutableStateFlow(AgentDashboardUiState())
    val uiState = _uiState.asStateFlow()

    fun loadFarms() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true)
            try {
                val response = api.getFarms()
                if (response.isSuccessful) {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        farms = response.body() ?: emptyMap(),
                        error = null
                    )
                } else {
                    _uiState.value = _uiState.value.copy(isLoading = false, error = response.message())
                }
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(isLoading = false, error = e.message)
            }
        }
    }

    fun onboardFarm(name: String, district: String, crop: String, phone: String, acres: Double) {
        viewModelScope.launch {
            try {
                val response = api.onboardFarm(OnboardRequest(name, district, crop, phone, acres))
                if (response.isSuccessful) {
                    loadFarms()
                } else {
                    _uiState.value = _uiState.value.copy(error = "Onboarding failed: ${response.message()}")
                }
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(error = e.message)
            }
        }
    }
}
