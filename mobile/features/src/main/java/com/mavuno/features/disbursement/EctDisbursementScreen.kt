package com.mavuno.features.disbursement

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Bolt
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun EctDisbursementScreen(
    viewModel: EctDisbursementViewModel,
    farmId: String,
    onBack: () -> Unit
) {
    val uiState by viewModel.uiState.collectAsState()
    var kwhAmount by remember { mutableStateOf("25") }
    var pumpNode by remember { mutableStateOf("PUMP-MBL-01") }

    LaunchedEffect(farmId) {
        viewModel.loadFarmer(farmId)
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Disburse ECT Tokens") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back")
                    }
                }
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
            uiState.farmer?.let { farmer ->
                Card(modifier = Modifier.fillMaxWidth()) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text("Farmer: ${farmer.name}", fontWeight = FontWeight.Bold)
                        Text("YPS Score: ${farmer.ypsScore}%", color = Color(0xFF2E7D32))
                        Text("Region: ${farmer.region}")
                    }
                }
            }

            OutlinedTextField(
                value = kwhAmount,
                onValueChange = { kwhAmount = it },
                label = { Text("Allocation (kWh)") },
                modifier = Modifier.fillMaxWidth(),
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                leadingIcon = { Icon(Icons.Default.Bolt, contentDescription = null) }
            )

            OutlinedTextField(
                value = pumpNode,
                onValueChange = { pumpNode = it },
                label = { Text("Pump Node ID") },
                modifier = Modifier.fillMaxWidth()
            )

            Spacer(modifier = Modifier.weight(1f))

            if (uiState.isSuccess) {
                Text(
                    "Token Disbursed Successfully!",
                    color = Color(0xFF2E7D32),
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.align(Alignment.CenterHorizontally)
                )
                Button(
                    onClick = onBack,
                    modifier = Modifier.fillMaxWidth().height(56.dp)
                ) {
                    Text("Return to Cockpit")
                }
            } else {
                Button(
                    onClick = {
                        val amount = kwhAmount.toIntOrNull() ?: 0
                        viewModel.disburseEct(farmId, uiState.farmer?.ypsScore ?: 0, amount, pumpNode)
                    },
                    modifier = Modifier.fillMaxWidth().height(56.dp),
                    enabled = !uiState.isLoading,
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF1B5E20))
                ) {
                    if (uiState.isLoading) {
                        CircularProgressIndicator(color = Color.White, modifier = Modifier.size(24.dp))
                    } else {
                        Text("Authorize Disbursement")
                    }
                }
            }

            uiState.error?.let {
                Text("Error: $it", color = MaterialTheme.colorScheme.error)
            }
        }
    }
}
