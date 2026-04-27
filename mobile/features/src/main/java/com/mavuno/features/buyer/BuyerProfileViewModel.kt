package com.mavuno.features.buyer

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mavuno.domain.model.BatchPayment
import com.mavuno.domain.model.BuyerProfile
import com.mavuno.domain.repository.BuyerRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.launch
import javax.inject.Inject

data class BuyerProfileUiState(
    val isLoading: Boolean = true,
    val profile: BuyerProfile? = null,
    val payments: List<BatchPayment> = emptyList(),
    val error: String? = null
)

@HiltViewModel
class BuyerProfileViewModel @Inject constructor(
    private val buyerRepository: BuyerRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(BuyerProfileUiState())
    val uiState: StateFlow<BuyerProfileUiState> = _uiState.asStateFlow()

    fun loadProfile(buyerId: String) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true)
            
            buyerRepository.syncBuyerData(buyerId)
            
            combine(
                buyerRepository.getBuyerProfile(buyerId),
                buyerRepository.getBatchPayments(buyerId)
            ) { profile, payments ->
                _uiState.value.copy(
                    isLoading = false,
                    profile = profile,
                    payments = payments
                )
            }.collect { state ->
                _uiState.value = state
            }
        }
    }

    fun logout(onSuccess: () -> Unit) {
        // Clear local credentials/cache if necessary
        onSuccess()
    }
}
