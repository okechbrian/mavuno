package com.mavuno.features.buyer

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.mavuno.domain.model.BatchPayment
import com.mavuno.domain.model.BuyerProfile
import java.text.SimpleDateFormat
import java.util.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun BuyerProfileScreen(
    viewModel: BuyerProfileViewModel,
    buyerId: String,
    onLogout: () -> Unit
) {
    val uiState by viewModel.uiState.collectAsState()

    LaunchedEffect(buyerId) {
        viewModel.loadProfile(buyerId)
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Buyer Account", fontWeight = FontWeight.Bold) },
                actions = {
                    IconButton(onClick = { viewModel.logout(onLogout) }) {
                        Icon(Icons.Default.Logout, contentDescription = "Logout")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = Color(0xFF1565C0),
                    titleContentColor = Color.White,
                    actionIconContentColor = Color.White
                )
            )
        }
    ) { padding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .background(Color(0xFFF8F9FA))
        ) {
            if (uiState.isLoading) {
                CircularProgressIndicator(modifier = Modifier.align(Alignment.Center), color = Color(0xFF1565C0))
            } else {
                LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(20.dp)
                ) {
                    item {
                        uiState.profile?.let { profile ->
                            BuyerHeader(profile)
                        }
                    }

                    item {
                        uiState.profile?.let { profile ->
                            BuyerStatsRow(profile)
                        }
                    }

                    item {
                        Text(
                            text = "Batch Payment History",
                            fontSize = 18.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFF1565C0)
                        )
                    }

                    if (uiState.payments.isEmpty()) {
                        item {
                            Box(modifier = Modifier.fillMaxWidth().padding(24.dp), contentAlignment = Alignment.Center) {
                                Text("No payment history found.", color = Color.Gray)
                            }
                        }
                    } else {
                        items(uiState.payments) { payment ->
                            BatchPaymentCard(payment)
                        }
                    }

                    item {
                        PreferredSuppliersSection()
                    }

                    item {
                        Spacer(modifier = Modifier.height(24.dp))
                        Button(
                            onClick = { viewModel.logout(onLogout) },
                            modifier = Modifier.fillMaxWidth(),
                            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFC62828)),
                            shape = RoundedCornerShape(12.dp)
                        ) {
                            Text("Logout from Portal")
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun BuyerHeader(profile: BuyerProfile) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
        shape = RoundedCornerShape(24.dp)
    ) {
        Row(
            modifier = Modifier.padding(20.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .size(64.dp)
                    .clip(CircleShape)
                    .background(Color(0xFFE3F2FD)),
                contentAlignment = Alignment.Center
            ) {
                Icon(Icons.Default.Business, contentDescription = null, tint = Color(0xFF1565C0), modifier = Modifier.size(32.dp))
            }
            Spacer(modifier = Modifier.width(16.dp))
            Column {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(text = profile.name, fontSize = 20.sp, fontWeight = FontWeight.Bold)
                    if (profile.isVerified) {
                        Spacer(modifier = Modifier.width(4.dp))
                        Icon(Icons.Default.Verified, contentDescription = "Verified", tint = Color(0xFF1565C0), modifier = Modifier.size(16.dp))
                    }
                }
                Text(text = profile.company, fontSize = 14.sp, color = Color.Gray)
                Text(text = profile.region, fontSize = 12.sp, color = Color.LightGray)
            }
        }
    }
}

@Composable
fun BuyerStatsRow(profile: BuyerProfile) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        ProfileStatCard(
            modifier = Modifier.weight(1f),
            title = "Total Vol",
            value = "${profile.totalVolumeKg}kg",
            icon = Icons.Default.Inventory,
            color = Color(0xFF1565C0)
        )
        ProfileStatCard(
            modifier = Modifier.weight(1f),
            title = "Contracts",
            value = profile.activeContracts.toString(),
            icon = Icons.Default.Description,
            color = Color(0xFF2E7D32)
        )
        ProfileStatCard(
            modifier = Modifier.weight(1f),
            title = "ECT Spent",
            value = String.format("%.1f", profile.ectSpent),
            icon = Icons.Default.Bolt,
            color = Color(0xFFD35400)
        )
    }
}

@Composable
fun ProfileStatCard(modifier: Modifier, title: String, value: String, icon: androidx.compose.ui.graphics.vector.ImageVector, color: Color) {
    Card(
        modifier = modifier,
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(
            modifier = Modifier.padding(12.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Icon(icon, contentDescription = null, tint = color, modifier = Modifier.size(20.dp))
            Spacer(modifier = Modifier.height(8.dp))
            Text(text = value, fontSize = 16.sp, fontWeight = FontWeight.Bold)
            Text(text = title, fontSize = 10.sp, color = Color.Gray)
        }
    }
}

@Composable
fun BatchPaymentCard(payment: BatchPayment) {
    val sdf = SimpleDateFormat("dd MMM yyyy, HH:mm", Locale.getDefault())
    val statusColor = when (payment.status) {
        "Settled" -> Color(0xFF2E7D32)
        "Pending" -> Color(0xFFF9A825)
        else -> Color(0xFFC62828)
    }

    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
    ) {
        Row(
            modifier = Modifier.padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(text = "Batch ID: ${payment.id}", fontWeight = FontWeight.Bold, fontSize = 14.sp)
                Text(text = sdf.format(Date(payment.timestamp)), fontSize = 12.sp, color = Color.Gray)
                Text(text = "${payment.offerCount} Offers included", fontSize = 12.sp, color = Color.Gray)
            }
            Column(horizontalAlignment = Alignment.End) {
                Text(
                    text = "UGX ${String.format("%,d", payment.totalAmountUgx)}",
                    fontWeight = FontWeight.ExtraBold,
                    fontSize = 16.sp,
                    color = Color.Black
                )
                Surface(
                    color = statusColor.copy(alpha = 0.1f),
                    shape = RoundedCornerShape(4.dp)
                ) {
                    Text(
                        text = payment.status.uppercase(),
                        modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp),
                        fontSize = 10.sp,
                        fontWeight = FontWeight.Bold,
                        color = statusColor
                    )
                }
            }
        }
    }
}

@Composable
fun PreferredSuppliersSection() {
    Column {
        Text(
            text = "Preferred Suppliers",
            fontSize = 18.sp,
            fontWeight = FontWeight.Bold,
            color = Color(0xFF1565C0),
            modifier = Modifier.padding(bottom = 12.dp)
        )
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(containerColor = Color.White),
            elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                SupplierRow("Nabasumba Regenerative Farm", "Coffee")
                HorizontalDivider(modifier = Modifier.padding(vertical = 8.dp), color = Color.LightGray.copy(alpha = 0.3f))
                SupplierRow("Mukisa Sustainable Hub", "Maize")
                HorizontalDivider(modifier = Modifier.padding(vertical = 8.dp), color = Color.LightGray.copy(alpha = 0.3f))
                SupplierRow("Central Valley Cooperative", "Multiple")
            }
        }
    }
}

@Composable
fun SupplierRow(name: String, crop: String) {
    Row(modifier = Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Icon(Icons.Default.Agriculture, contentDescription = null, tint = Color.Gray, modifier = Modifier.size(18.dp))
        Spacer(modifier = Modifier.width(12.dp))
        Column {
            Text(text = name, fontWeight = FontWeight.Bold, fontSize = 14.sp)
            Text(text = "Specialization: $crop", fontSize = 12.sp, color = Color.Gray)
        }
        Spacer(modifier = Modifier.weight(1f))
        Icon(Icons.Default.ChevronRight, contentDescription = null, tint = Color.LightGray)
    }
}
