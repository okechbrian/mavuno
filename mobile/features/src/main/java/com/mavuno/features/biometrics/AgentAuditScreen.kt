package com.mavuno.features.biometrics

import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Map
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.mavuno.core.util.MapNavigator
import com.mavuno.domain.model.HardwarePing
import com.mavuno.domain.repository.HardwarePingRepository
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AgentAuditScreen(
    hardwareScanner: HardwareScanner,
    repository: HardwarePingRepository,
    farmId: String
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var isScanning by remember { mutableStateOf(false) }
    var lastPing by remember { mutableStateOf<HardwarePing?>(null) }
    var snackbarHostState = remember { SnackbarHostState() }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbarHostState) },
        topBar = {
            TopAppBar(
                title = { Text("Farm Biometric Audit") },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = Color(0xFF1B5E20),
                    titleContentColor = Color.White
                )
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(text = "Auditing Farm: $farmId", fontWeight = FontWeight.Bold, fontSize = 18.sp)
                IconButton(onClick = { 
                    // Mock coordinates for Mbale region demo
                    MapNavigator.openMapAt(context, 1.08, 34.18, "Farm $farmId") 
                }) {
                    Icon(Icons.Default.Map, contentDescription = "View on Map", tint = Color(0xFF1B5E20))
                }
            }

            if (lastPing == null && !isScanning) {
                Box(modifier = Modifier.weight(1f).fillMaxWidth(), contentAlignment = Alignment.Center) {
                    Text("No data captured. Press scan to begin.", color = Color.Gray)
                }
            } else if (isScanning) {
                Box(modifier = Modifier.weight(1f).fillMaxWidth(), contentAlignment = Alignment.Center) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        CircularProgressIndicator(color = Color(0xFF1B5E20))
                        Spacer(modifier = Modifier.height(8.dp))
                        Text("Connecting to sensor...")
                    }
                }
            } else {
                lastPing?.let { ping ->
                    AuditDataCard(ping)
                }
            }

            Button(
                onClick = {
                    scope.launch {
                        isScanning = true
                        lastPing = hardwareScanner.scanSoilSensor(farmId)
                        isScanning = false
                    }
                },
                modifier = Modifier.fillMaxWidth().height(56.dp),
                enabled = !isScanning,
                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF1B5E20))
            ) {
                Text(if (isScanning) "Scanning..." else "Capture Biometrics")
            }

            if (lastPing != null) {
                Button(
                    onClick = {
                        scope.launch {
                            repository.savePingLocally(lastPing!!)
                            snackbarHostState.showSnackbar("Biometrics saved to local ledger")
                            lastPing = null
                        }
                    },
                    modifier = Modifier.fillMaxWidth().height(56.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF2E7D32))
                ) {
                    Icon(Icons.Default.CheckCircle, contentDescription = null)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("Verify & Save to Ledger")
                }
            }
        }
    }
}

@Composable
fun AuditDataCard(ping: HardwarePing) {
    Card(
        modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp),
        colors = CardDefaults.cardColors(containerColor = Color(0xFFF1F8E9))
    ) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("Soil Biometrics Captured", fontWeight = FontWeight.Bold)
            HorizontalDivider()
            BiometricRow("Soil Moisture", "${String.format("%.1f", ping.soilMoisture)}%")
            BiometricRow("Soil Temp", "${String.format("%.1f", ping.soilTemperature)}°C")
            BiometricRow("Nitrogen (N)", "${String.format("%.1f", ping.nitrogen)} mg/kg")
            BiometricRow("Phosphorus (P)", "${String.format("%.1f", ping.phosphorus)} mg/kg")
            BiometricRow("Potassium (K)", "${String.format("%.1f", ping.potassium)} mg/kg")
            BiometricRow("Signature", ping.signature.take(16) + "...")
        }
    }
}

@Composable
fun BiometricRow(label: String, value: String) {
    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(label, color = Color.Gray)
        Text(value, fontWeight = FontWeight.Medium, color = Color.Black)
    }
}
