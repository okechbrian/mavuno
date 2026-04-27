package com.mavuno.features.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mavuno.data.remote.MavunoApi
import com.mavuno.data.remote.model.LoginRequest
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class AuthUiState(
    val isLoading: Boolean = false,
    val error: String? = null,
    val successSubject: String? = null
)

@HiltViewModel
class AuthViewModel @Inject constructor(
    private val api: MavunoApi
) : ViewModel() {

    private val _uiState = MutableStateFlow(AuthUiState())
    val uiState = _uiState.asStateFlow()

    fun login(role: String, idOrPhone: String, passwordOrPin: String) {
        viewModelScope.launch {
            _uiState.value = AuthUiState(isLoading = true)
            try {
                // Role needs to be lowercase for API
                val apiRole = role.lowercase()
                val response = api.login(LoginRequest(apiRole, idOrPhone, passwordOrPin))
                
                if (response.isSuccessful && response.body()?.ok == true) {
                    val redirectUrl = response.body()?.redirect ?: ""
                    // Extract subject from redirect e.g. /farmer/UG-MBL-0001
                    val subject = redirectUrl.split("/").lastOrNull() ?: "admin"
                    _uiState.value = AuthUiState(isLoading = false, successSubject = subject)
                } else {
                    _uiState.value = AuthUiState(isLoading = false, error = "Invalid credentials. Please try again.")
                }
            } catch (e: Exception) {
                _uiState.value = AuthUiState(isLoading = false, error = "Network error: ${e.localizedMessage}")
            }
        }
    }
}
