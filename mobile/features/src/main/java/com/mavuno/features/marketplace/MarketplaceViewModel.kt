package com.mavuno.features.marketplace

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mavuno.domain.model.Offer
import com.mavuno.domain.repository.MarketplaceRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class MarketplaceUiState(
    val isLoading: Boolean = true,
    val offers: List<Offer> = emptyList(),
    val error: String? = null
)

@HiltViewModel
class MarketplaceViewModel @Inject constructor(
    private val marketplaceRepository: MarketplaceRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(MarketplaceUiState())
    val uiState: StateFlow<MarketplaceUiState> = _uiState.asStateFlow()

    init {
        loadMarketplace()
    }

    private fun loadMarketplace() {
        viewModelScope.launch {
            marketplaceRepository.getOpenOffers().collect { offers ->
                _uiState.value = MarketplaceUiState(
                    isLoading = false,
                    offers = offers
                )
            }
        }
    }

    fun acceptOffer(offerId: String, buyerId: String) {
        viewModelScope.launch {
            try {
                marketplaceRepository.acceptOffer(offerId, buyerId)
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(error = e.message)
            }
        }
    }
}
