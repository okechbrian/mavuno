package com.mavuno.features.biometrics

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Analytics
import androidx.compose.material.icons.filled.Payments
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
fun AgentDashboardScreen(
    viewModel: AgentDashboardViewModel,
    onNavigateToAudit: (String) -> Unit,
    onNavigateToDisburse: (String) -> Unit
) {
    val uiState by viewModel.uiState.collectAsState()
    var showOnboardDialog by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        viewModel.loadFarms()
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Agent Control Panel") },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = Color(0xFF1B5E20),
                    titleContentColor = Color.White
                )
            )
        },
        floatingActionButton = {
            FloatingActionButton(
                onClick = { showOnboardDialog = true },
                containerColor = Color(0xFFD35400)
            ) {
                Icon(Icons.Default.Add, contentDescription = "Onboard Farm", tint = Color.White)
            }
        }
    ) { padding ->
        if (uiState.isLoading) {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                CircularProgressIndicator()
            }
        } else {
            LazyColumn(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding),
                contentPadding = PaddingValues(16.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                items(uiState.farms.entries.toList()) { (farmId, farm) ->
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(containerColor = Color.White),
                        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        Column(modifier = Modifier.padding(16.dp)) {
                            Text(farm.farmer_name, fontWeight = FontWeight.Bold, fontSize = 18.sp)
                            Text("$farmId • ${farm.district} • ${farm.crop}", color = Color.Gray, fontSize = 12.sp)
                            
                            Spacer(modifier = Modifier.height(16.dp))
                            
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween
                            ) {
                                OutlinedButton(
                                    onClick = { onNavigateToAudit(farmId) },
                                    colors = ButtonDefaults.outlinedButtonColors(contentColor = Color(0xFF1B5E20))
                                ) {
                                    Icon(Icons.Default.Analytics, contentDescription = null, modifier = Modifier.size(16.dp))
                                    Spacer(Modifier.width(8.dp))
                                    Text("Audit")
                                }
                                
                                Button(
                                    onClick = { onNavigateToDisburse(farmId) },
                                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF2E7D32))
                                ) {
                                    Icon(Icons.Default.Payments, contentDescription = null, modifier = Modifier.size(16.dp))
                                    Spacer(Modifier.width(8.dp))
                                    Text("Disburse")
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    if (showOnboardDialog) {
        var name by remember { mutableStateOf("") }
        var district by remember { mutableStateOf("") }
        var crop by remember { mutableStateOf("") }
        var phone by remember { mutableStateOf("") }
        var acres by remember { mutableStateOf("") }

        AlertDialog(
            onDismissRequest = { showOnboardDialog = false },
            title = { Text("Onboard New Farmer") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(value = name, onValueChange = { name = it }, label = { Text("Farmer Name") }, singleLine = true)
                    OutlinedTextField(value = district, onValueChange = { district = it }, label = { Text("District") }, singleLine = true)
                    OutlinedTextField(value = crop, onValueChange = { crop = it }, label = { Text("Main Crop") }, singleLine = true)
                    OutlinedTextField(value = phone, onValueChange = { phone = it }, label = { Text("Phone Number") }, singleLine = true)
                    OutlinedTextField(value = acres, onValueChange = { acres = it }, label = { Text("Acres") }, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number), singleLine = true)
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        viewModel.onboardFarm(name, district, crop, phone, acres.toDoubleOrNull() ?: 1.0)
                        showOnboardDialog = false
                    },
                    enabled = name.isNotBlank() && district.isNotBlank() && crop.isNotBlank() && phone.isNotBlank()
                ) {
                    Text("Onboard")
                }
            },
            dismissButton = {
                TextButton(onClick = { showOnboardDialog = false }) {
                    Text("Cancel")
                }
            }
        )
    }
}