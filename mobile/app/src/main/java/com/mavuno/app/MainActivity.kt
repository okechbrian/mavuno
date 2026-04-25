package com.mavuno.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.History
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.QrCodeScanner
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
import com.mavuno.features.farmer.FarmerDashboardScreen
import com.mavuno.features.history.Transaction
import com.mavuno.features.history.TransactionHistoryScreen
import com.mavuno.features.verification.QrScannerScreen
import com.mavuno.features.verification.TokenVerifier
import com.mavuno.features.verification.VerificationResult
import dagger.hilt.android.AndroidEntryPoint
import javax.inject.Inject
import com.mavuno.core.R

@AndroidEntryPoint
class MainActivity : ComponentActivity() {

    @Inject
    lateinit var tokenVerifier: TokenVerifier

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                var loggedInFarmId by remember { mutableStateOf<String?>(null) }

                if (loggedInFarmId == null) {
                    LoginScreen(
                        role = "Farmer",
                        logoResId = R.drawable.ic_farmer_logo,
                        onLoginSuccess = { loggedInFarmId = it }
                    )
                } else {
                    MainScreen(tokenVerifier, loggedInFarmId!!)
                }
            }
        }
    }
}

sealed class Screen(val route: String, val label: String, val icon: ImageVector) {
    object Dashboard : Screen("dashboard", "Home", Icons.Default.Home)
    object Scanner : Screen("scanner", "Scan", Icons.Default.QrCodeScanner)
    object History : Screen("history", "History", Icons.Default.History)
}

@Composable
fun MainScreen(tokenVerifier: TokenVerifier, farmId: String) {
    val navController = rememberNavController()

    Scaffold(
        bottomBar = {
            BottomNavigationBar(navController)
        }
    ) { innerPadding ->
        NavHost(
            navController = navController,
            startDestination = Screen.Dashboard.route,
            modifier = Modifier.fillMaxSize().padding(innerPadding)
        ) {
            composable(Screen.Dashboard.route) {
                FarmerDashboardScreen(
                    viewModel = hiltViewModel(),
                    farmId = farmId
                )
            }
            composable(Screen.Scanner.route) {
                QrScannerScreen(
                    onTokenScanned = { data ->
                        val result = tokenVerifier.verifyToken(data)
                        if (result is VerificationResult.Success) {
                            navController.navigate(Screen.Dashboard.route)
                        }
                    },
                    onBack = { navController.popBackStack() }
                )
            }
            composable(Screen.History.route) {
                TransactionHistoryScreen(
                    title = "Farmer History",
                    transactions = listOf(
                        Transaction("1", "ECT Disbursed", "+25.00 ECT", System.currentTimeMillis() - 86400000, "Settled"),
                        Transaction("2", "Crop Offer", "500 KG", System.currentTimeMillis() - 172800000, "Open")
                    )
                )
            }
        }
    }
}

@Composable
fun BottomNavigationBar(navController: NavHostController) {
    val items = listOf(Screen.Dashboard, Screen.Scanner, Screen.History)
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
