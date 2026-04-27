package com.mavuno.features.biometrics

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mavuno.domain.model.HardwarePing
import com.mavuno.domain.model.HardwareScanResult
import com.mavuno.domain.repository.HardwarePingRepository
import com.mavuno.domain.repository.HardwareScanner
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.launch
import javax.inject.Inject

data class AgentAuditUiState(
    val isScanningBluetooth: Boolean = false,
    val isCameraMode: Boolean = false,
    val bluetoothDevices: List<HardwareScanResult> = emptyList(),
    val isConnecting: Boolean = false,
    val capturedPing: HardwarePing? = null,
    val error: String? = null,
    val saveSuccess: Boolean = false
)

@HiltViewModel
class AgentAuditViewModel @Inject constructor(
    private val hardwareScanner: HardwareScanner,
    private val pingRepository: HardwarePingRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(AgentAuditUiState())
    val uiState: StateFlow<AgentAuditUiState> = _uiState.asStateFlow()

    fun setCameraMode(enabled: Boolean) {
        _uiState.value = _uiState.value.copy(isCameraMode = enabled, isScanningBluetooth = false)
        if (enabled) {
            hardwareScanner.stopBluetoothScan()
        }
    }

    fun startBluetoothScan() {
        _uiState.value = _uiState.value.copy(
            isScanningBluetooth = true, 
            isCameraMode = false, 
            error = null
        )
        viewModelScope.launch {
            hardwareScanner.startBluetoothScan()
                .catch { e ->
                    _uiState.value = _uiState.value.copy(isScanningBluetooth = false, error = e.message)
                }
                .collect { devices ->
                    _uiState.value = _uiState.value.copy(bluetoothDevices = devices)
                }
        }
    }

    fun stopBluetoothScan() {
        hardwareScanner.stopBluetoothScan()
        _uiState.value = _uiState.value.copy(isScanningBluetooth = false)
    }

    fun connectToDevice(macAddress: String, farmId: String) {
        viewModelScope.launch {
            stopBluetoothScan()
            _uiState.value = _uiState.value.copy(isConnecting = true, error = null)
            try {
                val ping = hardwareScanner.connectAndPing(macAddress, farmId)
                _uiState.value = _uiState.value.copy(isConnecting = false, capturedPing = ping)
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(isConnecting = false, error = "Connection failed: ${e.message}")
            }
        }
    }

    fun fallbackCameraScan(qrCodeData: String, farmId: String) {
        // Prevent multiple simultaneous scan triggers
        if (_uiState.value.isConnecting || _uiState.value.capturedPing != null) return
        
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isConnecting = true, error = null, isCameraMode = false)
            try {
                val ping = hardwareScanner.fallbackCameraPing(qrCodeData, farmId)
                _uiState.value = _uiState.value.copy(isConnecting = false, capturedPing = ping)
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(isConnecting = false, error = "QR Scan failed: ${e.message}")
            }
        }
    }

    fun verifyAndSaveHarvest() {
        val ping = _uiState.value.capturedPing ?: return
        viewModelScope.launch {
            try {
                pingRepository.savePingLocally(ping)
                _uiState.value = _uiState.value.copy(saveSuccess = true, capturedPing = null)
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(error = "Failed to save ledger: ${e.message}")
            }
        }
    }

    fun clearState() {
        _uiState.value = AgentAuditUiState()
        stopBluetoothScan()
    }
}
