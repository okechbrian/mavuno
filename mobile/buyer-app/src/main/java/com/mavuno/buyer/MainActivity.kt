package com.mavuno.buyer

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Inventory
import androidx.compose.material.icons.filled.ShoppingCart
import androidx.compose.material.icons.filled.Store
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.mavuno.features.auth.LoginScreen
import com.mavuno.features.history.Transaction
import com.mavuno.features.history.TransactionHistoryScreen
import com.mavuno.features.marketplace.MarketplaceScreen
import dagger.hilt.android.AndroidEntryPoint
import com.mavuno.core.R

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                var loggedInBuyerId by remember { mutableStateOf<String?>(null) }

                if (loggedInBuyerId == null) {
                    LoginScreen(
                        role = "Buyer",
                        logoResId = R.drawable.ic_buyer_logo,
                        onLoginSuccess = { loggedInBuyerId = it }
                    )
                } else {
                    BuyerMainScreen(loggedInBuyerId!!)
                }
            }
        }
    }
}

sealed class BuyerScreen(val route: String, val label: String, val icon: ImageVector) {
    object Marketplace : BuyerScreen("marketplace", "Market", Icons.Default.Store)
    object MyBids : BuyerScreen("my_bids", "My Bids", Icons.Default.ShoppingCart)
    object Inventory : BuyerScreen("inventory", "Inventory", Icons.Default.Inventory)
}

@Composable
fun BuyerMainScreen(buyerId: String) {
    val navController = rememberNavController()

    Scaffold(
        bottomBar = {
            BuyerBottomBar(navController)
        }
    ) { innerPadding ->
        NavHost(
            navController = navController,
            startDestination = BuyerScreen.Marketplace.route,
            modifier = Modifier.fillMaxSize().padding(innerPadding)
        ) {
            composable(BuyerScreen.Marketplace.route) {
                MarketplaceScreen(
                    viewModel = hiltViewModel(),
                    buyerId = buyerId
                )
            }
            composable(BuyerScreen.MyBids.route) {
                TransactionHistoryScreen(
                    title = "My Active Bids",
                    transactions = listOf(
                        Transaction("B1", "Coffee Bid", "UGX 4500/KG", System.currentTimeMillis() - 1000000, "Pending")
                    )
                )
            }
            composable(BuyerScreen.Inventory.route) {
                TransactionHistoryScreen(
                    title = "Procurement Inventory",
                    transactions = listOf(
                        Transaction("I1", "Warehousing", "2,500 KG Maize", System.currentTimeMillis() - 5000000, "In Stock")
                    )
                )
            }
        }
    }
}

@Composable
fun BuyerBottomBar(navController: NavHostController) {
    val items = listOf(BuyerScreen.Marketplace, BuyerScreen.MyBids, BuyerScreen.Inventory)
    val navBackStackEntry by navController.currentBackStackEntryAsState()
    val currentRoute = navBackStackEntry?.destination?.route

    NavigationBar {
        items.forEach { screen ->
            NavigationBarItem(
                icon = { Icon(screen.icon, contentDescription = screen.label) },
                label = { Text(screen.label) },
                selected = currentRoute == screen.route,
                onClick = {
                    navController.navigate(screen.route) {
                        popUpTo(navController.graph.startDestinationId)
                        launchSingleTop = true
                    }
                }
            )
        }
    }
}
