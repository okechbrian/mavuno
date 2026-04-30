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
fun TradeFinancingApprovalScreen(
    viewModel: TradeFinancingApprovalViewModel,
    farmId: String,
    onBack: () -> Unit
) {
    val uiState by viewModel.uiState.collectAsState()
    var kgAmount by remember { mutableStateOf("25") }
    var aggregationPoint by remember { mutableStateOf("HUB-MBL-01") }

    LaunchedEffect(farmId) {
        viewModel.loadFarmer(farmId)
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Approve Trade Financing") },
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
                value = kgAmount,
                onValueChange = { kgAmount = it },
                label = { Text("Allocation (KG)") },
                modifier = Modifier.fillMaxWidth(),
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                leadingIcon = { Icon(Icons.Default.Bolt, contentDescription = null) }
            )

            OutlinedTextField(
                value = aggregationPoint,
                onValueChange = { aggregationPoint = it },
                label = { Text("Aggregation Point ID") },
                modifier = Modifier.fillMaxWidth()
            )

            Spacer(modifier = Modifier.weight(1f))

            if (uiState.isSuccess) {
                Text(
                    "Financing Approved Successfully!",
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
                        val amount = kgAmount.toIntOrNull() ?: 0
                        viewModel.approveFinancing(farmId, uiState.farmer?.ypsScore ?: 0, amount, aggregationPoint)
                    },
                    modifier = Modifier.fillMaxWidth().height(56.dp),
                    enabled = !uiState.isLoading,
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF1B5E20))
                ) {
                    if (uiState.isLoading) {
                        CircularProgressIndicator(color = Color.White, modifier = Modifier.size(24.dp))
                    } else {
                        Text("Approve Priority Financing")
                    }
                }
            }

            uiState.error?.let {
                Text("Error: $it", color = MaterialTheme.colorScheme.error)
            }
        }
    }
}
