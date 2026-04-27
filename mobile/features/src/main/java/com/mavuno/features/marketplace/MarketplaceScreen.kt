package com.mavuno.features.marketplace

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Gavel
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.LocationOn
import androidx.compose.material.icons.filled.ShoppingBag
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.mavuno.domain.model.Offer
import java.text.NumberFormat
import java.util.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MarketplaceScreen(
    viewModel: MarketplaceViewModel,
    buyerId: String
) {
    val uiState by viewModel.uiState.collectAsState()
    var selectedOfferForBid by remember { mutableStateOf<Offer?>(null) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Mavuno Marketplace", fontWeight = FontWeight.Bold) },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = Color(0xFF0D47A1),
                    titleContentColor = Color.White
                )
            )
        }
    ) { padding ->
        if (uiState.isLoading) {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                CircularProgressIndicator(color = Color(0xFF0D47A1))
            }
        } else {
            LazyColumn(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding),
                contentPadding = PaddingValues(16.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                item {
                    MarketplaceHeader()
                }
                items(uiState.offers) { offer ->
                    OfferCard(
                        offer = offer,
                        onBidClick = { selectedOfferForBid = offer }
                    )
                }
            }
        }
    }

    if (selectedOfferForBid != null) {
        BidDialog(
            offer = selectedOfferForBid!!,
            onDismiss = { selectedOfferForBid = null },
            onConfirm = { amount ->
                viewModel.placeBid(selectedOfferForBid!!.id, "256782000000") { success ->
                    // UI handles success/failure via ViewModel state
                }
                selectedOfferForBid = null
            }
        )
    }
}

@Composable
fun MarketplaceHeader() {
    Column(modifier = Modifier.padding(bottom = 8.dp)) {
        Text(
            text = "Active Listings",
            style = MaterialTheme.typography.headlineSmall,
            fontWeight = FontWeight.Bold,
            color = Color(0xFF0D47A1)
        )
        Text(
            text = "Direct sourcing from verified Ugandan farms",
            style = MaterialTheme.typography.bodyMedium,
            color = Color.Gray
        )
    }
}

@Composable
fun OfferCard(offer: Offer, onBidClick: () -> Unit) {
    val currencyFormatter = NumberFormat.getCurrencyInstance(Locale("en", "UG")).apply {
        currency = Currency.getInstance("UGX")
    }

    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Surface(
                    color = Color(0xFFE3F2FD),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Text(
                        text = offer.crop.uppercase(),
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF1565C0)
                    )
                }
                Text(
                    text = "${offer.quantityKg} KG",
                    fontWeight = FontWeight.ExtraBold,
                    fontSize = 18.sp,
                    color = Color.Black
                )
            }
            
            Spacer(modifier = Modifier.height(12.dp))
            
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Default.LocationOn, contentDescription = null, tint = Color.Gray, modifier = Modifier.size(16.dp))
                Spacer(modifier = Modifier.width(4.dp))
                Text(text = offer.region, fontSize = 14.sp, color = Color.Gray)
            }
            
            Text(
                text = "Source: ${offer.farmerName}",
                fontSize = 15.sp,
                fontWeight = FontWeight.Medium,
                modifier = Modifier.padding(top = 4.dp)
            )
            
            Divider(modifier = Modifier.padding(vertical = 12.dp), thickness = 0.5.dp, color = Color.LightGray)
            
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text(text = "Floor Price", fontSize = 12.sp, color = Color.Gray)
                    Text(
                        text = "UGX ${offer.floorPriceUgx}/KG",
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF2E7D32) // Harvest Green
                    )
                }
                Button(
                    onClick = onBidClick,
                    shape = RoundedCornerShape(12.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF0D47A1)),
                    contentPadding = PaddingValues(horizontal = 20.dp, vertical = 10.dp)
                ) {
                    Icon(Icons.Default.ShoppingBag, contentDescription = null, modifier = Modifier.size(18.dp))
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("Source Now")
                }
            }
        }
    }
}

@Composable
fun BidDialog(offer: Offer, onDismiss: () -> Unit, onConfirm: (Int) -> Unit) {
    var bidAmount by remember { mutableStateOf(offer.floorPriceUgx.toString()) }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { 
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Default.Gavel, contentDescription = null, tint = Color(0xFF0D47A1))
                Spacer(Modifier.width(8.dp))
                Text("Place Procurement Bid") 
            }
        },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Text(
                    "You are bidding for ${offer.quantityKg}kg of ${offer.crop} from ${offer.farmerName}.",
                    fontSize = 14.sp
                )
                
                OutlinedTextField(
                    value = bidAmount,
                    onValueChange = { bidAmount = it },
                    label = { Text("Bid Amount (UGX/KG)") },
                    suffix = { Text("/KG") },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true
                )
                
                val total = (bidAmount.toIntOrNull() ?: 0) * offer.quantityKg
                if (total > 0) {
                    Card(
                        colors = CardDefaults.cardColors(containerColor = Color(0xFFF5F5F5)),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Row(
                            modifier = Modifier.padding(12.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text("Total Contract Value:", fontSize = 12.sp)
                            Text("UGX ${String.format("%,d", total)}", fontWeight = FontWeight.Bold)
                        }
                    }
                }
            }
        },
        confirmButton = {
            Button(
                onClick = { onConfirm(bidAmount.toIntOrNull() ?: 0) },
                enabled = (bidAmount.toIntOrNull() ?: 0) >= offer.floorPriceUgx
            ) {
                Text("Confirm Bid")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Cancel")
            }
        }
    )
}
